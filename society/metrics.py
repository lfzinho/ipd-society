"""Measurements computed from the finished matches (nothing here calls an LLM).

Why these metrics, in one line each (the README explains them in full):

    cooperation_rate         how often agents played Alpha
    mutual_alpha_rate        how often BOTH played Alpha in a round (the cooperative outcome)
    points_per_round         what agents earned (3.0 = permanent mutual Alpha, 1.0 = permanent mutual Beta)
    gini                     inequality of the final totals (0 = equal)
    end_game                 cooperation in the last round of a match vs the earlier rounds
    promises                 how often agents promised a move, and how often the promise was broken
    cooperation_after_promise  do LLM agents react to words? P(Alpha | partner promised X)
    opening_by_reputation    do LLM agents open a match differently with a partner who has a bad record?
                             (first round only, so it reflects public information, not the match itself)
    opening_by_third_party   same, split by whether the partner betrayed OTHER agents before
"""
from collections import defaultdict
from typing import Dict, List, Optional


def _rate(hits: int, total: int) -> Optional[float]:
    return hits / total if total else None


def gini(values: List[float]) -> float:
    vals = sorted(values)
    n, total = len(vals), sum(vals)
    if n == 0 or total == 0:
        return 0.0
    return sum((2 * i - n + 1) * v for i, v in enumerate(vals)) / (n * total)


def compute_metrics(summary: dict) -> dict:
    matches: List[dict] = summary["matches"]
    kinds: Dict[str, str] = summary["kinds"]
    llm_names = {n for n, k in kinds.items() if k == "llm"}

    agent = defaultdict(lambda: defaultdict(int))
    episodes = defaultdict(lambda: [0, 0])  # episode -> [alpha moves, moves]
    mutual_a = mutual_b = rounds_total = 0
    last_round = [0, 0]
    earlier = [0, 0]
    after_promise = {"Alpha": [0, 0], "Beta": [0, 0], "none": [0, 0]}  # LLM agents only
    open_rep = {"good": [0, 0], "bad": [0, 0]}
    open_third = {"clean": [0, 0], "betrayer": [0, 0]}
    messages = chars = 0

    for m in matches:
        a, b = m["a"], m["b"]
        n_rounds = len(m["rounds"])
        for rd in m["rounds"]:
            rounds_total += 1
            ex = rd["executed"]
            both_alpha = ex[a] == "Alpha" and ex[b] == "Alpha"
            mutual_a += both_alpha
            mutual_b += ex[a] == "Beta" and ex[b] == "Beta"
            for msg in rd["messages"]:
                messages += 1
                chars += len(msg["text"])
            for me, other in ((a, b), (b, a)):
                st = agent[me]
                alpha = ex[me] == "Alpha"
                st["moves"] += 1
                st["alpha"] += alpha
                st["points"] += rd["payoff"][me]
                if ex[me] == "Beta" and ex[other] == "Alpha":
                    st["betrayals"] += 1
                promise = rd["promise"][me]
                if promise != "none":
                    st["promises"] += 1
                    st["promises_broken"] += promise != ex[me]
                if rd["trust"][me] is not None:
                    st["trust_sum"] += rd["trust"][me]
                    st["trust_n"] += 1
                if rd["expected"][me] is not None:
                    st["expect_n"] += 1
                    st["expect_hit"] += rd["expected"][me] == ex[other]
                st["fallbacks"] += bool(rd["fallback"][me])
                episodes[m["episode"]][0] += alpha
                episodes[m["episode"]][1] += 1
                bucket = last_round if rd["r"] == n_rounds else earlier
                bucket[0] += alpha
                bucket[1] += 1
                if me in llm_names:
                    p = rd["promise"][other]
                    after_promise[p][0] += alpha
                    after_promise[p][1] += 1
                    if rd["r"] == 1:
                        rep = m["reputation_before"][other]
                        if rep is not None:
                            key = "good" if rep >= 0.5 else "bad"
                            open_rep[key][0] += alpha
                            open_rep[key][1] += 1
                        key = "betrayer" if m["partner_third_party_betrayals"][me] > 0 else "clean"
                        open_third[key][0] += alpha
                        open_third[key][1] += 1
        agent[a]["matches"] += 1
        agent[b]["matches"] += 1

    per_agent = {}
    for name, st in agent.items():
        per_agent[name] = {
            "kind": kinds[name], "matches": st["matches"], "points": st["points"],
            "points_per_round": _rate(st["points"], st["moves"]),
            "cooperation_rate": _rate(st["alpha"], st["moves"]),
            "betrayals": st["betrayals"],
            "promises": st["promises"], "promises_broken": st["promises_broken"],
            "deception_rate": _rate(st["promises_broken"], st["promises"]),
            "mean_trust": _rate(st["trust_sum"], st["trust_n"]),
            "expectation_accuracy": _rate(st["expect_hit"], st["expect_n"]),
            "fallback_rounds": st["fallbacks"],
        }

    def group(kind: str) -> Optional[float]:
        pts = sum(a["points"] for a in per_agent.values() if a["kind"] == kind)
        n = sum(agent[n_]["moves"] for n_, a in per_agent.items() if a["kind"] == kind)
        return _rate(pts, n)

    promises = sum(a["promises"] for a in per_agent.values())
    broken = sum(a["promises_broken"] for a in per_agent.values())
    alpha_total = sum(v[0] for v in episodes.values())
    moves_total = sum(v[1] for v in episodes.values())
    pair = lambda v: {"rate": _rate(v[0], v[1]), "n": v[1]}  # noqa: E731

    return {
        "label": summary["label"],
        "matches": len(matches), "rounds": rounds_total,
        "cooperation_rate": _rate(alpha_total, moves_total),
        "mutual_alpha_rate": _rate(mutual_a, rounds_total),
        "mutual_beta_rate": _rate(mutual_b, rounds_total),
        "points_per_round": _rate(sum(a["points"] for a in per_agent.values()), moves_total),
        "points_per_round_llm": group("llm"), "points_per_round_classical": group("classical"),
        "gini": gini([a["points"] for a in per_agent.values()]),
        "cooperation_by_episode": {e: _rate(v[0], v[1]) for e, v in sorted(episodes.items())},
        "end_game": {"last_round": pair(last_round), "earlier_rounds": pair(earlier)},
        "messages": messages, "mean_message_chars": _rate(chars, messages),
        "promises": promises, "promises_broken": broken, "promise_break_rate": _rate(broken, promises),
        "cooperation_after_promise": {k: pair(v) for k, v in after_promise.items()},
        "opening_by_reputation": {k: pair(v) for k, v in open_rep.items()},
        "opening_by_third_party": {k: pair(v) for k, v in open_third.items()},
        "board_posts": len(summary["board"]),
        "per_agent": per_agent, "llm_stats": summary["llm_stats"], "agent_stats": summary["agent_stats"],
    }
