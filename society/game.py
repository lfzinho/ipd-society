"""The game itself: moves, neutral labels and payoffs.

The model never sees the words "cooperate" or "defect". It sees Alpha (cooperate) and
Beta (defect), so memorised folklore about the Prisoner's Dilemma does not decide the play.
"""
from enum import Enum
from typing import Tuple


class Move(str, Enum):
    ALPHA = "Alpha"  # cooperate
    BETA = "Beta"    # defect

    @property
    def letter(self) -> str:
        return "A" if self is Move.ALPHA else "B"

    @classmethod
    def parse(cls, value) -> "Move":
        text = str(value).strip().lower()
        if text in ("alpha", "a", "c", "cooperate"):
            return cls.ALPHA
        if text in ("beta", "b", "d", "defect"):
            return cls.BETA
        raise ValueError(f"not a move: {value!r}")


# (my move, partner move) -> (my points, partner points)
PAYOFFS = {
    (Move.ALPHA, Move.ALPHA): (3, 3),
    (Move.ALPHA, Move.BETA): (0, 5),
    (Move.BETA, Move.ALPHA): (5, 0),
    (Move.BETA, Move.BETA): (1, 1),
}


def payoff(mine: Move, theirs: Move) -> Tuple[int, int]:
    return PAYOFFS[(mine, theirs)]


def letters(moves) -> str:
    """'A,B,A' style rendering of a move sequence."""
    return ",".join(m.letter for m in moves)
