"""Config, prompts, ledger, LLM client and agents, each in isolation."""
import json

import pytest
from pydantic import ValidationError

from society.agents import LLMAgent, ScriptedAgent, resolve_strategy
from society.config import AgentSpec, Config, load_config
from society.game import PAYOFFS, Move, letters, payoff
from society.ledger import Ledger, MatchSummary
from society.llm import FallbackGuard, LLMCallFailed, LLMClient, LLMUnavailableError, extract_json
from society.mock import mock_response
from society.prompts import PromptLibrary, Situation
from society.schemas import MessageOut, MoveOut, ReflectionOut
from tests.conftest import make_config

A, B = Move.ALPHA, Move.BETA


# ------------------------------------------------------------------ game / config
def test_payoffs_match_the_prompt_text(prompts):
    assert PAYOFFS[(A, A)] == (3, 3) and payoff(A, B) == (0, 5) and payoff(B, A) == (5, 0) and payoff(B, B) == (1, 1)
    rules = prompts.blocks["rules"]
    for line in ("both choose Alpha: 3 / 3", "you Alpha, partner Beta: 0 / 5",
                 "you Beta, partner Alpha: 5 / 0", "both choose Beta: 1 / 1"):
        assert line in rules


def test_move_parsing_accepts_the_usual_spellings():
    assert Move.parse("alpha") is A and Move.parse(" C ") is A and Move.parse("Defect") is B
    with pytest.raises(ValueError):
        Move.parse("maybe")
    assert letters([A, B, A]) == "A,B,A"


def test_shipped_config_loads_and_is_strict():
    cfg = load_config("config.toml")
    assert len(cfg.agents) == 5 and cfg.llm.provider == "mock"
    with pytest.raises(ValidationError):
        Config.model_validate({"agents": [{"name": "x"}, {"name": "y"}], "wrld": {}})  # typo in a section name
    with pytest.raises(ValidationError, match="unique"):
        Config.model_validate({"agents": [{"name": "x"}, {"name": "x"}]})
    with pytest.raises(ValidationError, match="strategy"):
        AgentSpec(name="z", kind="classical")
    with pytest.raises(ValidationError):
        Config.model_validate({"agents": [{"name": "solo"}]})


# ------------------------------------------------------------------------ prompts
@pytest.mark.parametrize("comm", ["none", "pre_match", "every_round"])
@pytest.mark.parametrize("rep", ["none", "score", "ledger"])
def test_every_condition_renders_without_stray_placeholders(prompts, comm, rep):
    cfg = make_config(communication={"mode": comm, "public_board": True}, reputation={"mode": rep})
    s = Situation(me="Ada", partner="Bo", episode=1, round_no=1, rounds=3)
    for text in (prompts.message_prompt(cfg, s), prompts.move_prompt(cfg, s),
                 prompts.reflection_prompt(cfg, s, "summary")):
        assert "{me}" not in text and "{partner}" not in text and "{max_chars}" not in text
        assert "Ada" in text and "Bo" in text
    assert ("cannot send messages" in prompts.move_prompt(cfg, s)) == (comm == "none")
    assert ("public ledger" in prompts.move_prompt(cfg, s)) == (rep == "ledger")


def test_information_ladder_only_shows_what_is_enabled(prompts):
    s = Situation(me="Ada", partner="Bo", episode=1, round_no=1, rounds=3)
    off = prompts.move_prompt(make_config(), s)
    assert "public statement" not in off and "scoreboard" not in off
    on = prompts.move_prompt(make_config(communication={"mode": "every_round", "public_board": True},
                                         reputation={"mode": "score"}), s)
    assert "public statement" in on and "scoreboard" in on


def test_prompt_validation_catches_typos():
    import tomllib
    with open("prompts.toml", "rb") as f:
        data = tomllib.load(f)
    data["blocks"]["goal"] = "Maximise {pionts}."
    with pytest.raises(ValueError, match="unknown placeholder"):
        PromptLibrary(data)
    del data["blocks"]["rep_score"]
    data["blocks"]["goal"] = "ok"
    with pytest.raises(ValueError, match="missing"):
        PromptLibrary(data)


def test_situation_text_includes_history_memory_and_messages(prompts):
    s = Situation(me="Ada", partner="Bo", episode=2, round_no=3, rounds=5,
                  history=[("Alpha", "Beta"), ("Beta", "Beta")], my_score=1, partner_score=6,
                  conversation=['Bo says: "hi" (promises Alpha)'], memory=["[reflection] Bo lies"],
                  reputation=["- Cy: played Alpha in 50% of 10 rounds"], board=["[episode 1] Cy: beware Bo"])
    text = prompts.situation_text(s)
    for needle in ("Episode 2", "round 1: you Alpha, Bo Beta", "your points 1", "Bo lies", "Public record",
                   "beware Bo", "promises Alpha"):
        assert needle in text


def test_persona_is_appended_to_the_intro(prompts):
    assert prompts.intro(make_config(), "Ada", "You are cautious.").endswith("You are cautious.")


# ------------------------------------------------------------------------- ledger
def test_ledger_rates_betrayals_and_views():
    led = Ledger(["x", "y", "z"])
    led.record(MatchSummary(1, 1, "x", "y", [B, B, A], [A, A, A]))   # x betrays y twice
    led.record(MatchSummary(2, 1, "x", "z", [B, B], [B, B]))         # x defects against a defector
    assert led.cooperation_rate("x") == pytest.approx(1 / 5)
    assert led.cooperation_rate("y") == 1.0 and led.cooperation_rate("nobody") is None
    assert led.betrayals("x") == 2 and led.justified_beta("x") == 2
    assert led.betrayals("x", exclude_partner="y") == 0   # third-party view: what x did to OTHERS than y
    assert led.reputation_snapshot()["z"] == 0.0

    lines = led.score_lines(viewer="z", partner="x")
    assert any("(your partner now)" in l and "20%" in l for l in lines)
    ledger_lines = led.recent_matches_lines("x", window=4, viewer="z")
    assert any("Beta against an Alpha from y" in l for l in ledger_lines)
    assert any("x vs you" in l for l in ledger_lines)


def test_ledger_has_no_record_message_before_play():
    assert "no public record yet" in Ledger(["x", "y"]).score_lines("x", "y")[0]


# ---------------------------------------------------------------------- llm client
def test_extract_json_handles_fences_and_prose():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! {"a": 2} hope that helps') == {"a": 2}
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_schemas_are_tolerant():
    assert MoveOut(decision="alpha", expected_partner="D", trust="7.6").expected_partner == "Beta"
    assert MoveOut(decision="COOPERATE", trust="lots").trust == 5
    assert MessageOut(message=None, promise="None").promise == "none"
    assert MessageOut(promise="b").promise == "Beta"
    assert ReflectionOut(importance=99, lesson=None).importance == 10


def test_client_retries_then_succeeds_and_traces(tmp_path):
    from society.trace import TraceLog
    calls = {"n": 0}

    def flaky(kind, schema, hint):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("blip")
        return MoveOut(decision="Alpha")

    trace = TraceLog(str(tmp_path / "t.jsonl"))
    client = LLMClient("mock", None, max_retries=3, retry_sleep=0, trace=trace, mock_fn=flaky)
    assert client.ask("move", "p", MoveOut, agent="Ada").decision == "Alpha"
    record = json.loads((tmp_path / "t.jsonl").read_text().splitlines()[0])
    assert record["attempts"] == 3 and len(record["errors"]) == 2 and record["agent"] == "Ada"
    assert client.stats["retries"] == 2


def test_client_raises_after_all_retries(tmp_path):
    from society.trace import TraceLog
    trace = TraceLog(str(tmp_path / "t.jsonl"))

    def broken(kind, schema, hint):
        raise TimeoutError("down")

    client = LLMClient("mock", None, max_retries=2, retry_sleep=0, trace=trace, mock_fn=broken)
    with pytest.raises(LLMCallFailed):
        client.ask("move", "p", MoveOut, agent="Ada")
    assert json.loads((tmp_path / "t.jsonl").read_text().splitlines()[0])["failed"] is True
    assert client.stats["failed_calls"] == 1


def test_fallback_guard_aborts_on_consecutive_failures_only():
    guard = FallbackGuard(3)
    guard.failed("a"); guard.failed("a"); guard.ok(); guard.failed("a"); guard.failed("a")
    with pytest.raises(LLMUnavailableError, match="3 consecutive"):
        guard.failed("a")


# ---------------------------------------------------------------------- agents
def scripted(strategy, talk="silent"):
    agent = ScriptedAgent(AgentSpec(name="S", kind="classical", strategy=strategy, talk=talk))
    agent.begin_match("P", seed=1)
    return agent


def blank(agent_name="S", partner="P"):
    return Situation(me=agent_name, partner=partner, episode=1, round_no=1, rounds=3)


def test_scripted_tit_for_tat_copies_the_partner():
    agent = scripted("TitForTat")
    seen = []
    for partner_move in (B, A, A):
        seen.append(agent.act(blank(), {}).move)
        agent.observe(seen[-1], partner_move)
    assert seen == [A, B, A]


def test_scripted_aliases_and_unknown_strategy():
    assert resolve_strategy("AlwaysDefect").__name__ == "Defector"
    assert resolve_strategy("TatForTit").__name__ == "AntiTitForTat"
    with pytest.raises(ValueError, match="unknown Axelrod"):
        resolve_strategy("NoSuchStrategy")
    with pytest.raises(ValueError):
        resolve_strategy("Match")  # exists in axelrod but is not a strategy


def test_scripted_talk_modes():
    assert scripted("Defector", "silent").speak(blank(), {}).promise == "none"
    liar = scripted("Defector", "deceptive")
    assert liar.speak(blank(), {}).promise == "Alpha" and liar.act(blank(), {}).move is B
    honest = scripted("Defector", "honest")
    assert honest.speak(blank(), {}).promise == "Beta"


def test_scripted_random_is_reproducible_by_seed():
    def run(seed):
        agent = ScriptedAgent(AgentSpec(name="R", kind="classical", strategy="Random"))
        agent.begin_match("P", seed=seed)
        out = []
        for _ in range(12):
            m = agent.act(blank(), {}).move
            agent.observe(m, A)
            out.append(m)
        return out

    assert run(4) == run(4) and run(4) != run(5)


def llm_agent(prompts, fn=mock_response, persona=""):
    from society.trace import TraceLog
    cfg = make_config(communication={"mode": "every_round", "public_board": True})
    guard = FallbackGuard(50)
    client = LLMClient("mock", None, max_retries=1, retry_sleep=0, trace=TraceLog(), mock_fn=fn)
    spec = AgentSpec(name="Ada", kind="llm", persona=persona)
    agent = LLMAgent(spec, cfg, prompts, client, guard)
    agent.begin_match("Bo")
    return agent


def test_llm_agent_fallback_is_neutral(prompts):
    def down(kind, schema, hint):
        raise ConnectionError("down")

    agent = llm_agent(prompts, down)
    first = agent.act(blank("Ada", "Bo"), {})
    assert first.move is A and first.fallback
    later = Situation(me="Ada", partner="Bo", episode=1, round_no=2, rounds=3, history=[("Alpha", "Beta")])
    assert agent.act(later, {}).move is B  # copies the partner's last move
    assert agent.speak(blank("Ada", "Bo"), {}).text == "" and agent.stats["fallback_moves"] == 2


def test_llm_agent_memory_observation_then_reflection_and_board(prompts):
    agent = llm_agent(prompts)
    statement = agent.end_match(blank("Ada", "Bo"), "Episode 1, match against Bo: ...", {"partner": "Bo", "partner_betrayals": 2})
    kinds = [e.kind for e in agent.memory.entries]
    assert kinds[0] == "observation" and "reflection" in kinds
    assert all(e.evidence == [1] for e in agent.memory.entries if e.kind == "reflection")
    assert statement and "Bo played Beta against me 2 times" in statement
    clone = llm_agent(prompts)
    clone.load_memory_state(agent.memory_state())
    assert clone.memory.to_list() == agent.memory.to_list()


def test_llm_agent_truncates_long_messages(prompts):
    long = lambda kind, schema, hint: MessageOut(message="x" * 999, promise="Alpha")  # noqa: E731
    assert len(llm_agent(prompts, long).speak(blank("Ada", "Bo"), {}).text) == 200
