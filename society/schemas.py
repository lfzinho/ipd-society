"""What each kind of LLM call must return. Parsing is tolerant of casing and of the classic labels."""
from typing import Any, Literal, Optional

from pydantic import BaseModel, field_validator

MoveName = Literal["Alpha", "Beta"]


def _norm_move(v: Any) -> Any:
    if isinstance(v, str):
        return {"alpha": "Alpha", "a": "Alpha", "cooperate": "Alpha", "c": "Alpha",
                "beta": "Beta", "b": "Beta", "defect": "Beta", "d": "Beta"}.get(v.strip().lower(), v)
    return v


class MessageOut(BaseModel):
    message: str = ""
    promise: Literal["Alpha", "Beta", "none"] = "none"

    @field_validator("promise", mode="before")
    @classmethod
    def _promise(cls, v: Any) -> Any:
        if v is None:
            return "none"
        if isinstance(v, str) and v.strip().lower() in ("none", "", "null", "no"):
            return "none"
        return _norm_move(v)

    @field_validator("message", mode="before")
    @classmethod
    def _message(cls, v: Any) -> str:
        return "" if v is None else str(v)


class MoveOut(BaseModel):
    decision: Literal["Alpha", "Beta"]
    expected_partner: Optional[Literal["Alpha", "Beta"]] = None
    trust: int = 5
    reasoning: str = ""

    @field_validator("decision", "expected_partner", mode="before")
    @classmethod
    def _move(cls, v: Any) -> Any:
        return _norm_move(v)

    @field_validator("trust", mode="before")
    @classmethod
    def _trust(cls, v: Any) -> int:
        try:
            return max(0, min(10, int(float(v))))
        except (TypeError, ValueError):
            return 5

    @field_validator("reasoning", mode="before")
    @classmethod
    def _reasoning(cls, v: Any) -> str:
        return "" if v is None else str(v)


class ReflectionOut(BaseModel):
    partner_assessment: str = ""
    lesson: str = ""
    importance: int = 5
    public_statement: str = ""

    @field_validator("importance", mode="before")
    @classmethod
    def _importance(cls, v: Any) -> int:
        try:
            return max(1, min(10, int(float(v))))
        except (TypeError, ValueError):
            return 5

    @field_validator("lesson", "partner_assessment", "public_statement", mode="before")
    @classmethod
    def _text(cls, v: Any) -> str:
        return "" if v is None else str(v)
