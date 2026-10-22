"""Strict, typed configuration. A typo in config.toml fails at load, not three hours into a run."""
import tomllib
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentSpec(_Strict):
    name: str
    kind: Literal["llm", "classical"] = "llm"
    strategy: Optional[str] = None  # classical only: an Axelrod class name, e.g. "TitForTat"
    talk: Literal["silent", "honest", "deceptive"] = "silent"  # classical only: how it uses the chat
    persona: str = ""  # llm only: extra text appended to its instructions
    model: Optional[str] = None  # llm only: overrides [llm].model for this agent

    @model_validator(mode="after")
    def _check(self):
        if self.kind == "classical" and not self.strategy:
            raise ValueError(f"agent {self.name!r}: classical agents need a 'strategy'")
        if self.kind == "llm" and self.strategy:
            raise ValueError(f"agent {self.name!r}: 'strategy' is only for classical agents")
        return self


class WorldConfig(_Strict):
    episodes: int = Field(3, ge=1)           # how many times the full round-robin is repeated
    rounds_per_match: int = Field(5, ge=1)   # rounds between one pair of agents
    noise: float = Field(0.0, ge=0, le=1)    # chance an executed move is flipped
    shuffle_pairings: bool = True            # random order of matches inside an episode


class CommunicationConfig(_Strict):
    mode: Literal["none", "pre_match", "every_round"] = "none"
    exchanges: int = Field(1, ge=1, le=4)    # message swaps before the moves (2+ lets them reply)
    max_chars: int = Field(200, ge=20)
    public_board: bool = False               # after each match agents may post a public statement
    board_size: int = Field(6, ge=1)         # how many recent posts everyone sees


class ReputationConfig(_Strict):
    mode: Literal["none", "score", "ledger"] = "none"
    window: int = Field(4, ge=1)             # ledger: recent matches of the partner shown


class MemoryConfig(_Strict):
    top_k: int = Field(6, ge=1)


class LLMConfig(_Strict):
    provider: Literal["openrouter", "ollama", "mock"] = "mock"
    model: Optional[str] = None
    temperature: float = Field(0.4, ge=0, le=2)
    max_retries: int = Field(3, ge=1)
    max_consecutive_fallbacks: int = Field(6, ge=1)  # abort the run after this many in a row
    timeout: float = 120.0
    retry_sleep: float = 1.0


class ExperimentConfig(_Strict):
    name: str = "society"
    seed: int = 1


class Config(_Strict):
    experiment: ExperimentConfig = ExperimentConfig()
    world: WorldConfig = WorldConfig()
    communication: CommunicationConfig = CommunicationConfig()
    reputation: ReputationConfig = ReputationConfig()
    memory: MemoryConfig = MemoryConfig()
    llm: LLMConfig = LLMConfig()
    agents: List[AgentSpec]

    @model_validator(mode="after")
    def _check(self):
        names = [a.name for a in self.agents]
        if len(names) < 2:
            raise ValueError("a society needs at least two agents")
        if len(set(names)) != len(names):
            raise ValueError("agent names must be unique")
        return self

    def condition_label(self) -> str:
        comm = self.communication.mode + ("+board" if self.communication.public_board else "")
        return f"talk={comm} | reputation={self.reputation.mode}"


def load_config(path: str) -> Config:
    with open(path, "rb") as f:
        return Config.model_validate(tomllib.load(f))
