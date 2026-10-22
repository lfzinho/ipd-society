"""The society: schedules the matches, runs each round, keeps the public record, saves progress.

One *episode* is a full round-robin (every pair plays one match of `rounds_per_match` rounds).
A run is `episodes` of them. Inside a round the order is always:

    1. message phase   (only if communication is on): `exchanges` swaps; both agents write at the
                       same time, then read each other's message
    2. move phase      both choose Alpha/Beta at the same time
    3. noise           an executed move may be flipped (config `noise`)
    4. both agents observe the executed moves

After a match: the ledger is updated, each agent stores an observation and reflects, and an
agent may post a public statement to the board. Everything is appended to `matches.jsonl`;
`state.json` holds what is needed to resume (memories, board, finished match ids).
"""
import hashlib
import itertools
import json
import os
import random
from typing import Dict, List, Optional

from society.agents import Agent, Decision, LLMAgent, ScriptedAgent, Utterance
from society.config import Config
from society.game import Move, letters, payoff
from society.ledger import Ledger, MatchSummary
from society.llm import FallbackGuard, LLMClient
from society.mock import mock_response
from society.prompts import PromptLibrary, Situation
from society.trace import TraceLog


class Society:
    def __init__(self, config: Config, prompts: PromptLibrary, output_dir: str, verbose: bool = True):
        self.config = config
        self.prompts = prompts
        self.output_dir = output_dir
        self.verbose = verbose
        os.makedirs(output_dir, exist_ok=True)

        self.trace = TraceLog(os.path.join(output_dir, "trace.jsonl"))
        self.guard = FallbackGuard(config.llm.max_consecutive_fallbacks)
        self.clients: Dict[Optional[str], LLMClient] = {}
        self.agents: Dict[str, Agent] = {spec.name: self._build_agent(spec) for spec in config.agents}

        self.ledger = Ledger(list(self.agents))
        self.matches: List[dict] = []
        self.board: List[dict] = []
        self.totals: Dict[str, int] = {n: 0 for n in self.agents}

    # ----------------------------------------------------------------- setup
    def _client(self, model: Optional[str]) -> LLMClient:
        key = model or self.config.llm.model
        if key not in self.clients:
            c = self.config.llm
            self.clients[key] = LLMClient(
                c.provider, key, temperature=c.temperature, max_retries=c.max_retries, timeout=c.timeout,
                retry_sleep=c.retry_sleep, trace=self.trace, mock_fn=mock_response,
            )
        return self.clients[key]

    def _build_agent(self, spec) -> Agent:
        if spec.kind == "classical":
            return ScriptedAgent(spec)
        return LLMAgent(spec, self.config, self.prompts, self._client(spec.model), self.guard)

    def schedule(self) -> List[tuple]:
        """Deterministic list of (match_id, episode, agent_a, agent_b)."""
        names = list(self.agents)
        out, match_id = [], 0
        for episode in range(1, self.config.world.episodes + 1):
            pairs = list(itertools.combinations(names, 2))
            if self.config.world.shuffle_pairings:
                random.Random(self.config.experiment.seed * 7919 + episode).shuffle(pairs)
            for a, b in pairs:
                match_id += 1
                out.append((match_id, episode, a, b))
        return out

    # ------------------------------------------------------------ persistence
    def _paths(self):
        return (os.path.join(self.output_dir, "matches.jsonl"), os.path.join(self.output_dir, "state.json"))

    def _fingerprint(self) -> str:
        return hashlib.sha1(self.config.model_dump_json().encode()).hexdigest()

    def _save(self, record: dict):
        matches_path, state_path = self._paths()
        with open(matches_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        state = {
            "fingerprint": self._fingerprint(),
            "done": [m["match_id"] for m in self.matches],
            "board": self.board,
            "memory": {n: a.memory_state() for n, a in self.agents.items() if a.memory_state() is not None},
        }
        tmp = state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, state_path)

    def _resume(self):
        matches_path, state_path = self._paths()
        if not (os.path.exists(matches_path) and os.path.exists(state_path)):
            return
        try:
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
            if state.get("fingerprint") != self._fingerprint():
                raise ValueError("the config differs from the saved run")
            done = set(state["done"])
            with open(matches_path, encoding="utf-8") as f:
                records = [json.loads(line) for line in f if line.strip()]
            records = [r for r in records if r["match_id"] in done]
            if {r["match_id"] for r in records} != done:
                raise ValueError("matches.jsonl does not contain every finished match")
        except Exception as e:
            print(f"WARNING: could not resume from {self.output_dir} ({e}). Starting from scratch.")
            for p in self._paths():
                if os.path.exists(p):
                    os.remove(p)
            return
        with open(matches_path, "w", encoding="utf-8") as f:  # drop any record written after the last state save
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
        for r in records:
            self._apply_to_ledger(r)
        self.matches = records
        self.board = state["board"]
        for name, mem in state["memory"].items():
            self.agents[name].load_memory_state(mem)
        print(f"Resuming: {len(records)} matches already finished.")

    # ----------------------------------------------------------------- views
    def _apply_to_ledger(self, record: dict):
        a, b = record["a"], record["b"]
        self.ledger.record(MatchSummary(
            record["match_id"], record["episode"], a, b,
            [Move.parse(r["executed"][a]) for r in record["rounds"]],
            [Move.parse(r["executed"][b]) for r in record["rounds"]],
        ))
        self.totals[a] += record["score"][a]
        self.totals[b] += record["score"][b]

    def _reputation_lines(self, me: str, partner: str) -> List[str]:
        mode = self.config.reputation.mode
        if mode == "none":
            return []
        lines = self.ledger.score_lines(me, partner)
        if mode == "ledger":
            recent = self.ledger.recent_matches_lines(partner, self.config.reputation.window, viewer=me)
            if recent:
                lines += [f"Recent matches of {partner}:"] + recent
        return lines

    def _board_lines(self) -> List[str]:
        if not self.config.communication.public_board:
            return []
        recent = self.board[-self.config.communication.board_size:]
        return [f"[episode {p['episode']}] {p['author']}: {p['text']}" for p in recent]

    def _situation(self, me: str, partner: str, episode: int, round_no: int, hist: Dict[str, list],
                   conversation: List[Utterance]) -> Situation:
        h = hist[me]
        return Situation(
            me=me, partner=partner, episode=episode, round_no=round_no, rounds=self.config.world.rounds_per_match,
            history=[(m.value, t.value) for m, t in h],
            conversation=[f"{u.speaker} says: \"{u.text}\"" + (f" (promises {u.promise})" if u.promise != "none" else "")
                          for u in conversation if u.text or u.promise != "none"],
            reputation=self._reputation_lines(me, partner), board=self._board_lines(),
            my_score=sum(payoff(m, t)[0] for m, t in h), partner_score=sum(payoff(m, t)[1] for m, t in h),
        )

    def _extras(self, me: str, partner: str, promised: Dict[str, str], kept: Dict[str, bool],
                betrayals_by_partner: int = 0) -> dict:
        rep = self.ledger.reputation(partner) if self.config.reputation.mode != "none" else None
        return {"partner_reputation": rep, "partner_promise": promised.get(partner, "none"),
                "partner_kept_promises": kept.get(partner, True), "partner_betrayals": betrayals_by_partner}

    # ------------------------------------------------------------- one match
    def _talks_in_round(self, round_no: int) -> bool:
        mode = self.config.communication.mode
        return mode == "every_round" or (mode == "pre_match" and round_no == 1)

    def play_match(self, match_id: int, episode: int, a: str, b: str) -> dict:
        cfg = self.config
        seed = cfg.experiment.seed * 1_000_003 + match_id
        rng = random.Random(seed)
        agents = {a: self.agents[a], b: self.agents[b]}
        pair = ((a, b), (b, a))

        reputation_before = self.ledger.reputation_snapshot()
        third_party = {a: self.ledger.betrayals(b, exclude_partner=a), b: self.ledger.betrayals(a, exclude_partner=b)}
        for me, other in pair:
            agents[me].begin_match(other, seed)

        hist: Dict[str, list] = {a: [], b: []}
        promised_all: Dict[str, List[str]] = {a: [], b: []}   # one promise per round, "none" if silent
        kept: Dict[str, bool] = {a: True, b: True}
        rounds: List[dict] = []

        for r in range(1, cfg.world.rounds_per_match + 1):
            conversation: List[Utterance] = []
            messages = []
            if self._talks_in_round(r):
                for ex in range(1, cfg.communication.exchanges + 1):
                    fresh = []
                    for me, other in pair:  # both write before reading each other's new message
                        s = self._situation(me, other, episode, r, hist, conversation)
                        x = self._extras(me, other, {other: _last_promise(conversation, other)}, kept)
                        fresh.append(agents[me].speak(s, x))
                    conversation += fresh
                    messages += [{"speaker": u.speaker, "text": u.text, "promise": u.promise, "exchange": ex,
                                  "fallback": u.fallback} for u in fresh]
            promise_now = {n: _last_promise(conversation, n) for n in (a, b)}

            decisions: Dict[str, Decision] = {}
            for me, other in pair:
                s = self._situation(me, other, episode, r, hist, conversation)
                x = self._extras(me, other, {other: promise_now[other]}, kept)
                decisions[me] = agents[me].act(s, x)

            executed = {}
            for n in (a, b):
                move = decisions[n].move
                if cfg.world.noise and rng.random() < cfg.world.noise:
                    move = Move.BETA if move is Move.ALPHA else Move.ALPHA
                executed[n] = move
            pa, pb = payoff(executed[a], executed[b])

            for me, other in pair:
                hist[me].append((executed[me], executed[other]))
                agents[me].observe(executed[me], executed[other])
                promised_all[me].append(promise_now[me])
                if promise_now[me] != "none" and promise_now[me] != executed[me].value:
                    kept[me] = False

            rounds.append({
                "r": r, "messages": messages,
                "promise": promise_now,
                "intended": {n: decisions[n].move.value for n in (a, b)},
                "executed": {n: executed[n].value for n in (a, b)},
                "expected": {n: (decisions[n].expected.value if decisions[n].expected else None) for n in (a, b)},
                "trust": {n: decisions[n].trust for n in (a, b)},
                "fallback": {n: decisions[n].fallback for n in (a, b)},
                "payoff": {a: pa, b: pb},
            })

        score = {n: sum(rd["payoff"][n] for rd in rounds) for n in (a, b)}
        record = {
            "match_id": match_id, "episode": episode, "a": a, "b": b, "rounds": rounds, "score": score,
            "reputation_before": {a: reputation_before[a], b: reputation_before[b]},
            "partner_third_party_betrayals": third_party,  # key = viewer; value = betrayals by its partner of others
        }
        self._apply_to_ledger(record)
        self._finish_match(record, hist)
        return record

    def _finish_match(self, record: dict, hist: Dict[str, list]):
        a, b, episode = record["a"], record["b"], record["episode"]
        for me, other in ((a, b), (b, a)):
            mine, theirs = [m for m, _ in hist[me]], [t for _, t in hist[me]]
            made = [rd["promise"][other] for rd in record["rounds"]]
            promises = [(p, t) for p, t in zip(made, theirs) if p != "none"]
            kept_n = sum(1 for p, t in promises if p == t.value)
            summary = (f"Episode {episode}, match against {other}: you played {letters(mine)}; {other} played "
                       f"{letters(theirs)}. You scored {record['score'][me]}, {other} scored {record['score'][other]}.")
            if promises:
                summary += f" {other} promised a move in {len(promises)} rounds and kept the promise in {kept_n}."
            s = self._situation(me, other, episode, len(hist[me]), hist, [])
            betrayals = sum(1 for m, t in zip(mine, theirs) if t is Move.BETA and m is Move.ALPHA)
            x = {"partner_betrayals": betrayals, "partner": other}
            statement = self.agents[me].end_match(s, summary, x)
            if statement:
                self.board.append({"episode": episode, "author": me, "text": statement})

    # ------------------------------------------------------------------- run
    def run(self) -> dict:
        self._resume()
        done = {m["match_id"] for m in self.matches}
        plan = self.schedule()
        for match_id, episode, a, b in plan:
            if match_id in done:
                continue
            record = self.play_match(match_id, episode, a, b)
            self.matches.append(record)
            self._save(record)
            if self.verbose:
                coop = sum(1 for rd in record["rounds"] for n in (a, b) if rd["executed"][n] == "Alpha")
                total = 2 * len(record["rounds"])
                print(f"[match {match_id}/{len(plan)} | episode {episode}] {a} {record['score'][a]} - "
                      f"{record['score'][b]} {b} | Alpha {coop}/{total}")
        return self.summary()

    def summary(self) -> dict:
        stats = {}
        for client in self.clients.values():
            for k, v in client.stats.items():
                stats[k] = stats.get(k, 0) + v
        agent_stats = {n: a.stats for n, a in self.agents.items() if isinstance(a, LLMAgent)}
        return {"label": self.config.condition_label(), "matches": self.matches, "totals": self.totals,
                "board": self.board, "llm_stats": stats, "agent_stats": agent_stats,
                "kinds": {n: a.kind for n, a in self.agents.items()}}


def _last_promise(conversation: List[Utterance], speaker: str) -> str:
    for u in reversed(conversation):
        if u.speaker == speaker and u.promise != "none":
            return u.promise
    return "none"
