"""The society end to end on the offline mock model."""
import json
import sys

import pytest

import main as main_module
from society import world as world_module
from society.llm import LLMUnavailableError
from society.metrics import compute_metrics, gini
from society.mock import mock_response
from society.report import comparison_table, run_report, verdicts
from society.world import Society
from tests.conftest import make_config


def run(cfg, prompts, tmp_path, name="out"):
    society = Society(cfg, prompts, str(tmp_path / name), verbose=False)
    return society, society.run()


def trace_prompts(tmp_path, name="out", kind=None):
    records = [json.loads(l) for l in (tmp_path / name / "trace.jsonl").read_text().splitlines()]
    return [r for r in records if kind is None or r["kind"] == kind]


def test_schedule_is_a_full_round_robin_per_episode(prompts, tmp_path):
    society = Society(make_config(), prompts, str(tmp_path))
    plan = society.schedule()
    assert len(plan) == 2 * 6   # 4 agents -> 6 pairs per episode, 2 episodes
    for episode in (1, 2):
        pairs = {frozenset((a, b)) for _, e, a, b in plan if e == episode}
        assert len(pairs) == 6
    assert [m[0] for m in plan] == list(range(1, 13))


def test_full_run_writes_every_artifact(prompts, tmp_path):
    cfg = make_config()
    main_module.run_one(cfg, prompts, str(tmp_path / "out"), verbose=False)
    for name in ("matches.jsonl", "state.json", "trace.jsonl", "metrics.json", "report.md"):
        assert (tmp_path / "out" / name).exists(), name
    assert "# Run report" in (tmp_path / "out" / "report.md").read_text()


def test_same_seed_is_reproducible_and_different_seed_differs(prompts, tmp_path):
    cfg = make_config(agents=[
        {"name": "Ada", "kind": "llm"},
        {"name": "Rob", "kind": "classical", "strategy": "Random"},
        {"name": "Dee", "kind": "classical", "strategy": "TitForTat"}])
    a = run(cfg, prompts, tmp_path, "a")[1]["matches"]
    b = run(cfg, prompts, tmp_path, "b")[1]["matches"]
    c = run(make_config(experiment={"seed": 99}, agents=[x.model_dump() for x in cfg.agents]), prompts, tmp_path, "c")[1]["matches"]
    assert a == b and a != c


@pytest.mark.parametrize("mode,exchanges,expect_rounds,per_round", [
    ("none", 1, 0, 0), ("pre_match", 1, 1, 2), ("every_round", 1, 3, 2), ("every_round", 2, 3, 4)])
def test_communication_modes_control_when_messages_exist(prompts, tmp_path, mode, exchanges, expect_rounds, per_round):
    cfg = make_config(communication={"mode": mode, "exchanges": exchanges}, world={"episodes": 1})
    record = run(cfg, prompts, tmp_path)[1]["matches"][0]
    talking = [rd for rd in record["rounds"] if rd["messages"]]
    assert len(talking) == expect_rounds
    assert all(len(rd["messages"]) == per_round for rd in talking)
    if mode == "pre_match":
        assert record["rounds"][0]["messages"] and not record["rounds"][1]["messages"]


def test_agents_write_before_reading_each_others_message(prompts, tmp_path):
    cfg = make_config(communication={"mode": "every_round", "exchanges": 2}, world={"episodes": 1, "rounds_per_match": 1})
    run(cfg, prompts, tmp_path)
    speak = [r for r in trace_prompts(tmp_path, kind="message") if r["agent"] in ("Ada", "Bo")]
    # In the first exchange nobody has said anything yet; in the second they have read each other.
    assert any("Messages this round" not in r["prompt"] for r in speak)
    assert any("Messages this round" in r["prompt"] for r in speak)


def test_reputation_reaches_the_prompt_only_when_enabled(prompts, tmp_path):
    off = make_config(reputation={"mode": "none"}, world={"episodes": 2})
    run(off, prompts, tmp_path, "off")
    assert not any("Public record" in r["prompt"] for r in trace_prompts(tmp_path, "off", "move"))
    on = make_config(reputation={"mode": "ledger"}, world={"episodes": 2})
    run(on, prompts, tmp_path, "on")
    moves = trace_prompts(tmp_path, "on", "move")
    assert any("Public record" in r["prompt"] and "Recent matches of" in r["prompt"] for r in moves)


def test_reputation_changes_behaviour_in_the_mock(prompts, tmp_path):
    """The mock opens with Beta against partners with a public record below 40% cooperation."""
    def opening_vs_eli(mode):
        cfg = make_config(reputation={"mode": mode}, world={"episodes": 3, "rounds_per_match": 2})
        record = run(cfg, prompts, tmp_path, f"rep-{mode}")[1]["matches"]
        firsts = [m["rounds"][0]["executed"][ag] for m in record for ag, other in ((m["a"], m["b"]), (m["b"], m["a"]))
                  if ag in ("Ada", "Bo") and other == "Eli" and m["episode"] > 1]
        return firsts

    assert all(x == "Alpha" for x in opening_vs_eli("none"))
    assert all(x == "Beta" for x in opening_vs_eli("ledger"))


def test_board_posts_are_visible_to_later_prompts(prompts, tmp_path):
    cfg = make_config(communication={"mode": "none", "public_board": True}, world={"episodes": 2})
    society, summary = run(cfg, prompts, tmp_path)
    assert summary["board"] and all(set(p) == {"episode", "author", "text"} for p in summary["board"])
    assert any("Public statements by agents" in r["prompt"] for r in trace_prompts(tmp_path, kind="move"))
    off = run(make_config(world={"episodes": 2}), prompts, tmp_path, "off")[1]
    assert off["board"] == []


def test_noise_flips_executed_moves_but_not_intentions(prompts, tmp_path):
    cfg = make_config(world={"episodes": 2, "noise": 0.5})
    matches = run(cfg, prompts, tmp_path)[1]["matches"]
    flips = sum(rd["intended"][n] != rd["executed"][n] for m in matches for rd in m["rounds"] for n in (m["a"], m["b"]))
    total = sum(2 * len(m["rounds"]) for m in matches)
    assert 0.25 * total < flips < 0.75 * total


def test_ledger_matches_the_recorded_moves(prompts, tmp_path):
    society, summary = run(make_config(), prompts, tmp_path)
    for name in society.agents:
        mine = [rd["executed"][name] for m in summary["matches"] if name in (m["a"], m["b"]) for rd in m["rounds"]]
        assert society.ledger.cooperation_rate(name) == pytest.approx(mine.count("Alpha") / len(mine))
    assert sum(summary["totals"].values()) == sum(sum(m["score"].values()) for m in summary["matches"])


def test_third_party_betrayal_counts_exclude_the_viewer(prompts, tmp_path):
    summary = run(make_config(world={"episodes": 2}), prompts, tmp_path)[1]
    last = [m for m in summary["matches"] if m["episode"] == 2][-1]
    # Eli betrays every Alpha it meets; by the end of the run a fresh opponent sees it as a known betrayer.
    if "Eli" in (last["a"], last["b"]):
        viewer = last["b"] if last["a"] == "Eli" else last["a"]
        assert last["partner_third_party_betrayals"][viewer] > 0


# ------------------------------------------------------------- failures and resume
def outage_after(n, monkeypatch):
    state = {"left": n}

    def flaky(kind, schema, hint):
        state["left"] -= 1
        if state["left"] < 0:
            raise ConnectionError("API down")
        return mock_response(kind, schema, hint)

    monkeypatch.setattr(world_module, "mock_response", flaky)
    return state


def test_outage_aborts_then_resume_gives_identical_results(prompts, tmp_path, monkeypatch):
    cfg = make_config(communication={"mode": "every_round"}, llm={"max_retries": 1, "max_consecutive_fallbacks": 3})
    full = run(cfg, prompts, tmp_path, "full")[1]["matches"]

    outage_after(40, monkeypatch)
    with pytest.raises(LLMUnavailableError, match="3 consecutive"):
        Society(cfg, prompts, str(tmp_path / "crash"), verbose=False).run()
    saved = [json.loads(l) for l in (tmp_path / "crash" / "matches.jsonl").read_text().splitlines()]
    assert 0 < len(saved) < len(full)

    monkeypatch.setattr(world_module, "mock_response", mock_response)
    resumed = Society(cfg, prompts, str(tmp_path / "crash"), verbose=False).run()["matches"]
    assert resumed == full
    trace = trace_prompts(tmp_path, "crash")
    assert any(r.get("failed") and "API down" in r["errors"][0] for r in trace)


def test_resume_ignores_a_state_from_a_different_config(prompts, tmp_path, capsys):
    run(make_config(), prompts, tmp_path)
    other = make_config(world={"episodes": 1})
    Society(other, prompts, str(tmp_path / "out"), verbose=False).run()
    assert "could not resume" in capsys.readouterr().out


def test_fallback_rounds_are_counted_and_flagged(prompts, tmp_path, monkeypatch):
    cfg = make_config(llm={"max_retries": 1, "max_consecutive_fallbacks": 100}, world={"episodes": 1})
    outage_after(12, monkeypatch)
    summary = run(cfg, prompts, tmp_path)[1]
    m = compute_metrics(summary)
    assert m["llm_stats"]["failed_calls"] > 0 and sum(a["fallback_rounds"] for a in m["per_agent"].values()) > 0
    assert verdicts(m)[0].startswith("FAIL")


# ------------------------------------------------------------------------ metrics
def test_gini_extremes():
    assert gini([5, 5, 5]) == 0 and gini([0, 0, 10]) == pytest.approx(2 / 3)
    assert gini([]) == 0


def test_metrics_detect_deception_and_reciprocal_trust(prompts, tmp_path):
    cfg = make_config(communication={"mode": "every_round"}, world={"episodes": 2})
    summary = run(cfg, prompts, tmp_path)[1]
    m = compute_metrics(summary)
    eli, dee = m["per_agent"]["Eli"], m["per_agent"]["Dee"]
    assert eli["deception_rate"] == 1.0                 # always promises Alpha, always plays Beta
    assert dee["deception_rate"] == 0.0                 # honest Tit For Tat keeps its word
    assert m["promise_break_rate"] and 0 < m["promise_break_rate"] < 1
    assert m["cooperation_after_promise"]["Alpha"]["n"] > 0
    assert 0 <= m["cooperation_rate"] <= 1 and m["rounds"] == len(summary["matches"]) * 3
    assert set(m["cooperation_by_episode"]) == {1, 2}


def test_report_and_comparison_render(prompts, tmp_path):
    results = {}
    for name, cond in main_module.CONDITIONS.items():
        cfg = main_module.with_overrides(make_config(world={"episodes": 1}), **cond)
        results[name] = compute_metrics(run(cfg, prompts, tmp_path, name)[1])
    table = comparison_table(results)
    for name in main_module.CONDITIONS:
        assert f"| {name} |" in table
    text = run_report(results["talk_watch"])
    for needle in ("## Verdicts", "## Agents", "Opening move, partner's public cooperation", "PASS"):
        assert needle in text


# --------------------------------------------------------------------------- CLI
def cli(monkeypatch, tmp_path, *extra):
    monkeypatch.setattr(sys, "argv", ["main.py", "--output-dir", str(tmp_path / "cli"), "--quiet", *extra])
    main_module.main()


def test_cli_runs_conditions_and_writes_comparison(monkeypatch, tmp_path):
    cli(monkeypatch, tmp_path, "--conditions", "baseline,talk", "--episodes", "1", "--rounds", "2")
    assert "| baseline |" in (tmp_path / "cli" / "comparison.md").read_text()
    assert (tmp_path / "cli" / "talk" / "report.md").exists()


def test_cli_rejects_unknown_condition(monkeypatch, tmp_path):
    with pytest.raises(SystemExit, match="Unknown condition"):
        cli(monkeypatch, tmp_path, "--conditions", "nonsense")


def test_cli_show_prompt_prints_without_running(monkeypatch, tmp_path, capsys):
    cli(monkeypatch, tmp_path, "--show-prompt", "move", "--communication", "every_round", "--reputation", "ledger", "--board")
    out = capsys.readouterr().out
    assert "Choose your move" in out and "public ledger" in out and "Messages this round" in out
    assert not (tmp_path / "cli").exists()


def test_cli_exits_with_code_2_on_outage(monkeypatch, tmp_path, capsys):
    outage_after(5, monkeypatch)
    monkeypatch.setattr("time.sleep", lambda s: None)
    with pytest.raises(SystemExit) as info:
        cli(monkeypatch, tmp_path, "--episodes", "1")
    assert info.value.code == 2 and "RUN STOPPED" in capsys.readouterr().out


def test_cli_multi_seed_aggregates_mean_and_sd(monkeypatch, tmp_path):
    cli(monkeypatch, tmp_path, "--conditions", "baseline,watch", "--seeds", "1,2", "--episodes", "1", "--rounds", "2")
    table = (tmp_path / "cli" / "comparison.md").read_text()
    assert "| baseline | 2 |" in table and "±" in table
    assert (tmp_path / "cli" / "watch" / "seed2" / "metrics.json").exists()
