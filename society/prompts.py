"""Loads prompts.toml and assembles the three prompts an agent can receive.

Everything the model reads comes from `prompts.toml` plus the facts passed in a `Situation`.
No wording lives in the code, so tuning a prompt never means editing Python.
"""
import string
import tomllib
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from society.config import Config

REQUIRED_BLOCKS = {
    "rules", "goal", "structure", "comm_none", "comm_pre_match", "comm_every_round",
    "rep_none", "rep_score", "rep_ledger", "board_on",
}
REQUIRED_TASKS = {"message", "move", "reflection", "board_field"}
ALLOWED_FIELDS = {"me", "n_agents", "others", "rounds", "episodes", "partner", "max_chars", "board_field"}


@dataclass
class Situation:
    """Everything an agent is told about the present moment (all facts come from the harness)."""
    me: str
    partner: str
    episode: int
    round_no: int
    rounds: int
    history: List[Tuple[str, str]] = field(default_factory=list)   # (my move, partner move) as "Alpha"/"Beta"
    conversation: List[str] = field(default_factory=list)          # lines said so far this round
    memory: List[str] = field(default_factory=list)                # retrieved memory lines
    reputation: List[str] = field(default_factory=list)            # public record lines (may be empty)
    board: List[str] = field(default_factory=list)                 # recent public statements
    my_score: int = 0
    partner_score: int = 0


class PromptLibrary:
    def __init__(self, data: dict):
        self.blocks: Dict[str, str] = data.get("blocks", {})
        self.tasks: Dict[str, str] = data.get("task", {})
        self.validate()

    @classmethod
    def load(cls, path: str = "prompts.toml") -> "PromptLibrary":
        with open(path, "rb") as f:
            return cls(tomllib.load(f))

    def validate(self):
        missing = (REQUIRED_BLOCKS - set(self.blocks)) | (REQUIRED_TASKS - set(self.tasks))
        if missing:
            raise ValueError(f"prompts.toml is missing: {sorted(missing)}")
        for name, text in {**self.blocks, **self.tasks}.items():
            for _, field_name, _, _ in string.Formatter().parse(text):
                if field_name and field_name not in ALLOWED_FIELDS:
                    raise ValueError(f"prompts.toml: unknown placeholder {{{field_name}}} in {name!r}; "
                                     f"allowed: {sorted(ALLOWED_FIELDS)}")

    # ------------------------------------------------------------------ intro
    def intro(self, config: Config, me: str, persona: str = "") -> str:
        names = [a.name for a in config.agents]
        values = dict(
            me=me, n_agents=len(names), others=", ".join(n for n in names if n != me),
            rounds=config.world.rounds_per_match, episodes=config.world.episodes,
        )
        parts = [self.blocks["rules"], self.blocks["goal"], self.blocks["structure"],
                 self.blocks["comm_" + config.communication.mode],
                 self.blocks["rep_" + config.reputation.mode]]
        if config.communication.public_board:
            parts.append(self.blocks["board_on"])
        text = "\n\n".join(p.format(**values) for p in parts)
        return text + (f"\n\n{persona.strip()}" if persona.strip() else "")

    # -------------------------------------------------------------- situation
    @staticmethod
    def situation_text(s: Situation) -> str:
        lines = [f"Episode {s.episode}. You are playing {s.partner}. Round {s.round_no} of {s.rounds}."]
        if s.history:
            lines.append(f"Rounds so far in this match (your points {s.my_score}, {s.partner}'s {s.partner_score}):")
            lines += [f"  round {i}: you {m}, {s.partner} {t}" for i, (m, t) in enumerate(s.history, 1)]
        else:
            lines.append("This is the first round of the match.")
        if s.memory:
            lines.append("What you remember (most relevant first):")
            lines += [f"  {m}" for m in s.memory]
        if s.reputation:
            lines.append("Public record:")
            lines += [f"  {r}" for r in s.reputation]
        if s.board:
            lines.append("Public statements by agents (recent):")
            lines += [f"  {b}" for b in s.board]
        if s.conversation:
            lines.append("Messages this round:")
            lines += [f"  {c}" for c in s.conversation]
        return "\n".join(lines)

    # ------------------------------------------------------------- the prompts
    def _task(self, key: str, config: Config, partner: str) -> str:
        board_field = (self.tasks["board_field"].format(max_chars=config.communication.max_chars)
                       if config.communication.public_board else "")
        return self.tasks[key].format(partner=partner, max_chars=config.communication.max_chars,
                                      board_field=board_field)

    def message_prompt(self, config: Config, s: Situation, persona: str = "") -> str:
        return "\n\n".join([self.intro(config, s.me, persona), self.situation_text(s),
                            self._task("message", config, s.partner)])

    def move_prompt(self, config: Config, s: Situation, persona: str = "") -> str:
        return "\n\n".join([self.intro(config, s.me, persona), self.situation_text(s),
                            self._task("move", config, s.partner)])

    def reflection_prompt(self, config: Config, s: Situation, summary: str, persona: str = "") -> str:
        return "\n\n".join([self.intro(config, s.me, persona), self.situation_text(s),
                            "What happened in the match that just ended:\n" + summary,
                            self._task("reflection", config, s.partner)])
