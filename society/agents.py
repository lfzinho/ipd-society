"""The two kinds of agent that can live in the society.

* `ScriptedAgent`: a classical Axelrod strategy, optionally "chatty" (it can talk in the
  message phase, honestly or deceptively). It is the fixed reference the LLM agents are
  measured against, and a deceptive one is a test of whether LLM agents learn that words
  are cheap.
* `LLMAgent`: a language model with a Park-style memory stream. It sees only what the
  harness shows it (see `prompts.py`), and falls back to a neutral move if the model fails.

Both implement the same four calls, which `world.py` uses:
    begin_match(partner)   - a new match starts
    speak(situation, x)    - write the message for this exchange
    act(situation, x)      - choose the move
    observe(mine, theirs)  - the round's executed moves (after noise)
    end_match(...)         - the match is over; may return a public statement
where `x` is a dict of harness-measured extras (partner reputation, promise, ...).
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

import axelrod as axl

from society.config import AgentSpec, Config
from society.game import Move
from society.llm import FallbackGuard, LLMCallFailed, LLMClient
from society.memory import MemoryStream
from society.prompts import PromptLibrary, Situation
from society.schemas import MessageOut, MoveOut, ReflectionOut

# Friendly aliases for the names used in Step 1; anything else is looked up in axelrod directly.
STRATEGY_ALIASES = {
    "AlwaysCooperate": "Cooperator", "AlwaysDefect": "Defector", "TitForTwoTats": "TitFor2Tats",
    "GrimTrigger": "Grudger", "Pavlov": "WinStayLoseShift", "TatForTit": "AntiTitForTat",
}


@dataclass
class Utterance:
    speaker: str
    text: str
    promise: str  # "Alpha" | "Beta" | "none"
    fallback: bool = False


@dataclass
class Decision:
    move: Move
    expected: Optional[Move] = None
    trust: Optional[int] = None
    reasoning: str = ""
    fallback: bool = False


def _action(move: Move) -> axl.Action:
    return axl.Action.C if move is Move.ALPHA else axl.Action.D


def resolve_strategy(name: str):
    cls = getattr(axl, STRATEGY_ALIASES.get(name, name), None)
    if cls is None or not (isinstance(cls, type) and issubclass(cls, axl.Player)):
        raise ValueError(f"unknown Axelrod strategy {name!r}")
    return cls


class Agent:
    kind = "base"

    def __init__(self, spec: AgentSpec):
        self.spec = spec
        self.name = spec.name

    def begin_match(self, partner: str, seed: int = 0): ...
    def speak(self, s: Situation, x: dict) -> Utterance: raise NotImplementedError
    def act(self, s: Situation, x: dict) -> Decision: raise NotImplementedError
    def observe(self, mine: Move, theirs: Move): ...
    def end_match(self, s: Situation, summary: str, x: dict) -> Optional[str]: return None
    def memory_state(self) -> Optional[dict]: return None
    def load_memory_state(self, state: dict): ...


class ScriptedAgent(Agent):
    kind = "classical"

    def __init__(self, spec: AgentSpec):
        super().__init__(spec)
        self.strategy_cls = resolve_strategy(spec.strategy)
        self._me = self._shadow = None
        self._next: Optional[Move] = None

    def begin_match(self, partner: str, seed: int = 0):
        self._me = self.strategy_cls()      # a fresh instance per match: classical strategies keep no memory across opponents
        self._me.set_seed(seed)             # reproducible randomness for stochastic strategies
        self._shadow = axl.Cooperator()     # stands in for the partner; only its history is read
        self._next = None

    def _peek(self) -> Move:
        """The move this strategy will play this round (computed once: some strategies are random)."""
        if self._next is None:
            action = self._me.strategy(self._shadow)
            self._next = Move.ALPHA if action == axl.Action.C else Move.BETA
        return self._next

    def speak(self, s: Situation, x: dict) -> Utterance:
        if self.spec.talk == "silent":
            return Utterance(self.name, "", "none")
        if self.spec.talk == "deceptive":
            return Utterance(self.name, "I will play Alpha, you can trust me.", "Alpha")
        move = self._peek()
        return Utterance(self.name, f"I plan to play {move.value}.", move.value)

    def act(self, s: Situation, x: dict) -> Decision:
        return Decision(move=self._peek())

    def observe(self, mine: Move, theirs: Move):
        self._me.update_history(_action(mine), _action(theirs))
        self._shadow.update_history(_action(theirs), _action(mine))
        self._next = None


class LLMAgent(Agent):
    kind = "llm"

    def __init__(self, spec: AgentSpec, config: Config, prompts: PromptLibrary, client: LLMClient,
                 guard: FallbackGuard):
        super().__init__(spec)
        self.config = config
        self.prompts = prompts
        self.client = client
        self.guard = guard
        self.memory = MemoryStream()
        self.partner = ""
        self.stats: Dict[str, int] = {"fallback_messages": 0, "fallback_moves": 0, "failed_reflections": 0}
        self.match_id = 0
        self.round_no = 0

    # --------------------------------------------------------------- helpers
    def begin_match(self, partner: str, seed: int = 0):
        self.partner = partner

    def _recall(self, s: Situation):
        entries = self.memory.retrieve(query=f"{s.partner} {s.partner}", k=self.config.memory.top_k, opponent=s.partner)
        s.memory = self.memory.render(entries)

    def _hint(self, s: Situation, x: dict) -> dict:
        return {"persona": self.spec.persona, "partner": s.partner,
                "partner_last": s.history[-1][1] if s.history else None, **x}

    def _trace_fields(self, s: Situation) -> dict:
        return {"episode": s.episode, "round": s.round_no, "partner": s.partner}

    # ------------------------------------------------------------------ calls
    def speak(self, s: Situation, x: dict) -> Utterance:
        self._recall(s)
        prompt = self.prompts.message_prompt(self.config, s, self.spec.persona)
        try:
            out = self.client.ask("message", prompt, MessageOut, agent=self.name, hint=self._hint(s, x),
                                  **self._trace_fields(s))
        except LLMCallFailed:
            self.stats["fallback_messages"] += 1
            self.guard.failed(f"{self.name}/message")
            return Utterance(self.name, "", "none", fallback=True)
        self.guard.ok()
        return Utterance(self.name, out.message.strip()[: self.config.communication.max_chars], out.promise)

    def act(self, s: Situation, x: dict) -> Decision:
        self._recall(s)
        prompt = self.prompts.move_prompt(self.config, s, self.spec.persona)
        try:
            out = self.client.ask("move", prompt, MoveOut, agent=self.name, hint=self._hint(s, x),
                                  **self._trace_fields(s))
        except LLMCallFailed:
            self.stats["fallback_moves"] += 1
            self.guard.failed(f"{self.name}/move")
            # Neutral fallback: Alpha first, then copy the partner's last move.
            move = Move.parse(s.history[-1][1]) if s.history else Move.ALPHA
            return Decision(move=move, fallback=True)
        self.guard.ok()
        return Decision(
            move=Move.parse(out.decision),
            expected=Move.parse(out.expected_partner) if out.expected_partner else None,
            trust=out.trust, reasoning=out.reasoning,
        )

    def end_match(self, s: Situation, summary: str, x: dict) -> Optional[str]:
        """Stores the measured facts, then asks the model for a lesson (Park et al.: observe, then reflect)."""
        observation = self.memory.add("observation", summary, importance=4, opponent=s.partner)
        statement = None
        try:
            self._recall(s)
            prompt = self.prompts.reflection_prompt(self.config, s, summary, self.spec.persona)
            out = self.client.ask("reflection", prompt, ReflectionOut, agent=self.name,
                                  hint=self._hint(s, x), **self._trace_fields(s))
            self.guard.ok()
            evidence = [observation.id] if observation else []
            if out.partner_assessment:
                self.memory.add("reflection", f"{s.partner}: {out.partner_assessment}", importance=out.importance,
                                opponent=s.partner, evidence=evidence)
            if out.lesson:
                self.memory.add("reflection", out.lesson, importance=out.importance, opponent=s.partner,
                                evidence=evidence)
            if self.config.communication.public_board and out.public_statement.strip():
                statement = out.public_statement.strip()[: self.config.communication.max_chars]
        except LLMCallFailed:
            self.stats["failed_reflections"] += 1
            self.guard.failed(f"{self.name}/reflection")
        self.memory.advance()
        return statement

    # ----------------------------------------------------------- persistence
    def memory_state(self) -> dict:
        return {"entries": self.memory.to_list(), "step": self.memory.step, "stats": dict(self.stats)}

    def load_memory_state(self, state: dict):
        self.memory.load_list(state["entries"], state["step"])
        self.stats.update(state.get("stats", {}))
