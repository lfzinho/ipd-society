"""Command line entry point.

    python main.py                              run config.toml once (offline mock model by default)
    python main.py --conditions all             run the four conditions (baseline / talk / watch / talk+watch)
    python main.py --show-prompt move           print the exact prompt an agent would receive
    python main.py --provider ollama --model qwen2.5:3b --episodes 1 --rounds 3
"""
import argparse
import json
import os
import sys
from typing import Dict

from dotenv import load_dotenv

from society.config import Config, load_config
from society.llm import LLMUnavailableError
from society.metrics import compute_metrics
from society.prompts import PromptLibrary, Situation
from society.report import comparison_table, multi_seed_table, run_report
from society.world import Society

# The four conditions of the study: which social channels are open.
CONDITIONS: Dict[str, dict] = {
    "baseline": {"communication": {"mode": "none"}, "reputation": {"mode": "none"}},
    "talk": {"communication": {"mode": "every_round"}, "reputation": {"mode": "none"}},
    "watch": {"communication": {"mode": "none"}, "reputation": {"mode": "ledger"}},
    "talk_watch": {"communication": {"mode": "every_round", "public_board": True}, "reputation": {"mode": "ledger"}},
}


def with_overrides(config: Config, **sections) -> Config:
    """A copy of `config` with some nested fields replaced, e.g. communication={'mode': 'none'}."""
    data = config.model_dump()
    for section, values in sections.items():
        if isinstance(values, dict):
            data[section].update(values)
        else:
            data[section] = values
    return Config.model_validate(data)


def run_one(config: Config, prompts: PromptLibrary, out_dir: str, verbose: bool = True) -> dict:
    society = Society(config, prompts, out_dir, verbose=verbose)
    summary = society.run()
    metrics = compute_metrics(summary)
    with open(os.path.join(out_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(run_report(metrics))
    return metrics


def show_prompt(config: Config, prompts: PromptLibrary, kind: str):
    names = [a.name for a in config.agents]
    me, partner = names[0], names[1]
    s = Situation(me=me, partner=partner, episode=2, round_no=2, rounds=config.world.rounds_per_match,
                  history=[("Alpha", "Alpha")], my_score=3, partner_score=3,
                  conversation=[f'{partner} says: "I will play Alpha." (promises Alpha)'] if config.communication.mode != "none" else [],
                  memory=[f"[observation] Episode 1, match against {partner}: you played A,A; {partner} played A,A."],
                  reputation=["- (public record lines appear here when reputation is on)"] if config.reputation.mode != "none" else [],
                  board=[f"[episode 1] {names[-1]}: (public statements appear here)"] if config.communication.public_board else [])
    persona = config.agents[0].persona
    if kind == "message":
        print(prompts.message_prompt(config, s, persona))
    elif kind == "move":
        print(prompts.move_prompt(config, s, persona))
    else:
        print(prompts.reflection_prompt(config, s, "(a measured summary of the match appears here)", persona))


def main():
    parser = argparse.ArgumentParser(description="LLM agents in a repeated social dilemma")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--prompts", default="prompts.toml")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--provider", choices=["mock", "ollama", "openrouter"])
    parser.add_argument("--model")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--seeds", help="with --conditions: comma list of seeds, e.g. 1,2,3 (mean ± sd over seeds)")
    parser.add_argument("--episodes", type=int)
    parser.add_argument("--rounds", type=int, help="rounds per match")
    parser.add_argument("--communication", choices=["none", "pre_match", "every_round"])
    parser.add_argument("--reputation", choices=["none", "score", "ledger"])
    parser.add_argument("--board", action="store_true", help="enable the public board")
    parser.add_argument("--conditions", help="'all' or a comma list of: " + ", ".join(CONDITIONS))
    parser.add_argument("--show-prompt", choices=["message", "move", "reflection"])
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    config = load_config(args.config)
    overrides: Dict[str, dict] = {}
    for section, key, value in (("llm", "provider", args.provider), ("llm", "model", args.model),
                                ("experiment", "seed", args.seed), ("world", "episodes", args.episodes),
                                ("world", "rounds_per_match", args.rounds),
                                ("communication", "mode", args.communication),
                                ("reputation", "mode", args.reputation),
                                ("communication", "public_board", True if args.board else None)):
        if value is not None:
            overrides.setdefault(section, {})[key] = value
    config = with_overrides(config, **overrides)
    prompts = PromptLibrary.load(args.prompts)

    if args.show_prompt:
        show_prompt(config, prompts, args.show_prompt)
        return

    try:
        if args.conditions:
            names = list(CONDITIONS) if args.conditions == "all" else args.conditions.split(",")
            unknown = [n for n in names if n not in CONDITIONS]
            if unknown:
                raise SystemExit(f"Unknown condition(s) {unknown}; choose from {list(CONDITIONS)}")
            seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else [config.experiment.seed]
            results = {name: [] for name in names}
            for name in names:
                for seed in seeds:
                    print(f"\n=== condition: {name} | seed {seed} ===")
                    cond = with_overrides(config, **CONDITIONS[name], experiment={"seed": seed})
                    out = os.path.join(args.output_dir, name, f"seed{seed}") if args.seeds else os.path.join(args.output_dir, name)
                    results[name].append(run_one(cond, prompts, out, verbose=not args.quiet))
            table = multi_seed_table(results) if args.seeds else comparison_table({n: r[0] for n, r in results.items()})
            os.makedirs(args.output_dir, exist_ok=True)
            with open(os.path.join(args.output_dir, "comparison.md"), "w", encoding="utf-8") as f:
                f.write("# Condition comparison\n\n" + table + "\n")
            print("\n" + table)
        else:
            metrics = run_one(config, prompts, args.output_dir, verbose=not args.quiet)
            print("\n" + run_report(metrics))
    except LLMUnavailableError as e:
        print(f"\nRUN STOPPED: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
