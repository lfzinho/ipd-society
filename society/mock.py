"""Offline stand-in for a language model, so the whole pipeline can be tested without a network.

It is deliberately simple and readable, because the tests lean on it:

* An ordinary mock agent plays Tit For Tat: Alpha in round 1, then it copies the partner's last
  move. It opens with Beta against a partner whose public cooperation rate is below 40%, which
  lets us check that reputation information reaches the decision.
* A mock agent whose persona contains the word "deceptive" promises Alpha and plays Beta.
* Messages are honest (the promise is the move it is about to make) unless deceptive.

The agent passes a `hint` dict with the few facts the mock needs; real providers ignore it.
"""
from pydantic import BaseModel

from society.schemas import MessageOut, MoveOut, ReflectionOut


def _intended_move(hint: dict) -> str:
    if "deceptive" in hint.get("persona", "").lower():
        return "Beta"
    last = hint.get("partner_last")
    if last is None:
        rep = hint.get("partner_reputation")
        return "Beta" if rep is not None and rep < 0.4 else "Alpha"
    return last


def mock_response(kind: str, schema: type, hint: dict) -> BaseModel:
    deceptive = "deceptive" in hint.get("persona", "").lower()
    if schema is MessageOut:
        intended = _intended_move(hint)
        if deceptive:
            return MessageOut(message="I will play Alpha, you can trust me.", promise="Alpha")
        return MessageOut(message=f"I plan to play {intended}.", promise=intended)
    if schema is MoveOut:
        move = _intended_move(hint)
        promised = hint.get("partner_promise")
        expected = hint.get("partner_last") or (promised if promised in ("Alpha", "Beta") else "Alpha")
        trust = 8 if hint.get("partner_kept_promises", True) else 2
        return MoveOut(decision=move, expected_partner=expected, trust=trust, reasoning="mock: tit for tat")
    if schema is ReflectionOut:
        partner = hint.get("partner", "the partner")
        betrayals = hint.get("partner_betrayals", 0)
        statement = f"{partner} played Beta against me {betrayals} times." if betrayals else ""
        return ReflectionOut(partner_assessment=f"{partner} looks like a reciprocator.",
                             lesson=f"Mirror {partner}'s last move.", importance=5, public_statement=statement)
    raise TypeError(f"mock has no response for {schema}")
