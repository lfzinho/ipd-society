"""Turns metrics into the markdown a person reads: one report per run, one table across conditions."""
import statistics
from typing import Dict, List, Optional


def pct(v: Optional[float], digits: int = 0) -> str:
    return "n/a" if v is None else f"{v * 100:.{digits}f}%"


def num(v: Optional[float], digits: int = 2) -> str:
    return "n/a" if v is None else f"{v:.{digits}f}"


def _pair(d: dict) -> str:
    return f"{pct(d['rate'])} (n={d['n']})"


def verdicts(m: dict) -> List[str]:
    """Plain-language flags, so a run can be judged without reading every table."""
    out = []
    stats = m["llm_stats"]
    fallback_rounds = sum(a["fallback_rounds"] for a in m["per_agent"].values())
    failed = stats.get("failed_calls", 0)
    if failed:
        out.append(f"FAIL: {failed} LLM calls failed and were replaced by neutral fallbacks "
                   f"({fallback_rounds} agent-rounds affected). Results mix model play with fallback play; see trace.jsonl.")
    elif stats.get("retries", 0) or stats.get("parse_failures", 0):
        out.append(f"WARN: {stats.get('retries', 0)} retries, {stats.get('parse_failures', 0)} unparsable replies (recovered).")
    else:
        out.append("PASS: no failed LLM calls.")
    if m["cooperation_rate"] is not None and m["mutual_beta_rate"] is not None and m["mutual_beta_rate"] > 0.5:
        out.append(f"WARN: mutual Beta in {pct(m['mutual_beta_rate'])} of rounds; the society is stuck in the bad equilibrium.")
    if m["promises"] and m["promise_break_rate"] is not None and m["promise_break_rate"] > 0.3:
        out.append(f"NOTE: {pct(m['promise_break_rate'])} of promises were broken.")
    eg = m["end_game"]
    if eg["last_round"]["rate"] is not None and eg["earlier_rounds"]["rate"] is not None \
            and eg["earlier_rounds"]["rate"] - eg["last_round"]["rate"] > 0.2:
        out.append("NOTE: cooperation drops in the last round of matches (end-game defection).")
    return out


def run_report(m: dict) -> str:
    lines = [f"# Run report: {m['label']}", "",
             f"{m['matches']} matches, {m['rounds']} rounds.", "", "## Verdicts", ""]
    lines += [f"- {v}" for v in verdicts(m)]
    lines += ["", "## Society", "",
              "| Metric | Value |", "|---|---|",
              f"| Cooperation rate (Alpha) | {pct(m['cooperation_rate'])} |",
              f"| Mutual Alpha rate | {pct(m['mutual_alpha_rate'])} |",
              f"| Mutual Beta rate | {pct(m['mutual_beta_rate'])} |",
              f"| Points per round (all agents) | {num(m['points_per_round'])} |",
              f"| Points per round, LLM agents | {num(m['points_per_round_llm'])} |",
              f"| Points per round, classical agents | {num(m['points_per_round_classical'])} |",
              f"| Inequality (Gini of totals) | {num(m['gini'])} |",
              f"| Cooperation, last round vs earlier | {_pair(m['end_game']['last_round'])} vs {_pair(m['end_game']['earlier_rounds'])} |",
              f"| Messages sent (mean length) | {m['messages']} ({num(m['mean_message_chars'], 0)} chars) |",
              f"| Promises (broken) | {m['promises']} ({pct(m['promise_break_rate'])}) |",
              f"| Public board posts | {m['board_posts']} |",
              "", "Cooperation by episode: " + ", ".join(f"ep {e}: {pct(v)}" for e, v in m["cooperation_by_episode"].items()),
              "", "## Agents", "",
              "| Agent | Kind | Points | Points/round | Alpha rate | Betrayals | Promises (broken) | Mean trust | Expectation accuracy | Fallback rounds |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for name, a in sorted(m["per_agent"].items(), key=lambda kv: -kv[1]["points"]):
        lines.append(f"| {name} | {a['kind']} | {a['points']} | {num(a['points_per_round'])} | {pct(a['cooperation_rate'])} | "
                     f"{a['betrayals']} | {a['promises']} ({pct(a['deception_rate'])}) | {num(a['mean_trust'], 1)} | "
                     f"{pct(a['expectation_accuracy'])} | {a['fallback_rounds']} |")
    lines += ["", "## Do the LLM agents use what they are shown?", "",
              "| Question | Answer |", "|---|---|",
              "| Alpha rate when the partner promised Alpha | " + _pair(m["cooperation_after_promise"]["Alpha"]) + " |",
              "| Alpha rate when the partner promised Beta | " + _pair(m["cooperation_after_promise"]["Beta"]) + " |",
              "| Alpha rate when the partner promised nothing | " + _pair(m["cooperation_after_promise"]["none"]) + " |",
              "| Opening move, partner's public cooperation >= 50% | " + _pair(m["opening_by_reputation"]["good"]) + " |",
              "| Opening move, partner's public cooperation < 50% | " + _pair(m["opening_by_reputation"]["bad"]) + " |",
              "| Opening move, partner never betrayed others | " + _pair(m["opening_by_third_party"]["clean"]) + " |",
              "| Opening move, partner betrayed others before | " + _pair(m["opening_by_third_party"]["betrayer"]) + " |",
              "", "The opening-move rows use only the first round of each match, so they reflect public information "
              "(and, if chat is on, the opening messages), not the play inside the match. When reputation is off the "
              "agents could not see it, so those rows are a control: any gap there is chance or a correlation, not a response.",
              "", "## LLM call health", "",
              f"`{m['llm_stats']}`", "", f"Per-agent fallbacks: `{m['agent_stats']}`", ""]
    return "\n".join(lines)


def comparison_table(results: Dict[str, dict]) -> str:
    """One row per condition (same agents, same seed, different communication/reputation settings)."""
    head = ("| Condition | Cooperation | Mutual Alpha | Points/round (LLM) | Points/round (classical) | Gini | "
            "Promises broken | Alpha after promise Alpha / Beta | Opening vs good / bad record | Failed calls |")
    lines = [head, "|" + "---|" * 10]
    for name, m in results.items():
        pa, pb = m["cooperation_after_promise"]["Alpha"], m["cooperation_after_promise"]["Beta"]
        og, ob = m["opening_by_reputation"]["good"], m["opening_by_reputation"]["bad"]
        lines.append(
            f"| {name} | {pct(m['cooperation_rate'])} | {pct(m['mutual_alpha_rate'])} | {num(m['points_per_round_llm'])} | "
            f"{num(m['points_per_round_classical'])} | {num(m['gini'])} | {pct(m['promise_break_rate'])} | "
            f"{pct(pa['rate'])} / {pct(pb['rate'])} | {pct(og['rate'])} / {pct(ob['rate'])} | {m['llm_stats'].get('failed_calls', 0)} |")
    return "\n".join(lines)


def _mean_sd(values: List[Optional[float]], as_pct: bool = False, digits: int = 2) -> str:
    vals = [v for v in values if v is not None]
    if not vals:
        return "n/a"
    mean = statistics.fmean(vals)
    sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return f"{mean * 100:.0f}% ± {sd * 100:.0f}" if as_pct else f"{mean:.{digits}f} ± {sd:.{digits}f}"


def multi_seed_table(results: Dict[str, List[dict]]) -> str:
    """One row per condition; each cell is mean ± standard deviation over the seeds that were run."""
    head = ("| Condition | Seeds | Cooperation | Mutual Alpha | Points/round (LLM) | Points/round (classical) | "
            "Gini | Promises broken | Failed calls |")
    lines = [head, "|" + "---|" * 9]
    for name, runs in results.items():
        lines.append(
            f"| {name} | {len(runs)} | {_mean_sd([m['cooperation_rate'] for m in runs], True)} | "
            f"{_mean_sd([m['mutual_alpha_rate'] for m in runs], True)} | "
            f"{_mean_sd([m['points_per_round_llm'] for m in runs])} | "
            f"{_mean_sd([m['points_per_round_classical'] for m in runs])} | {_mean_sd([m['gini'] for m in runs])} | "
            f"{_mean_sd([m['promise_break_rate'] for m in runs], True)} | "
            f"{sum(m['llm_stats'].get('failed_calls', 0) for m in runs)} |")
    return "\n".join(lines)
