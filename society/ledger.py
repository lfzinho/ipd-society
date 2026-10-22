"""The public record of who did what to whom (Step 3: reputation).

Every round of every match is appended here once the match is over. From it we derive
the reputation views agents may be shown, and the same data feeds the metrics, so what
the agents could see and what we measure never disagree.

Vocabulary used throughout:
    cooperation rate   share of an agent's moves that were Alpha
    betrayal           playing Beta in a round where the partner played Alpha
    justified Beta     playing Beta in a round where the partner also played Beta
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

from society.game import Move, letters


@dataclass
class MatchSummary:
    """One finished match as the ledger stores it (moves in round order)."""
    match_id: int
    episode: int
    a: str
    b: str
    moves_a: List[Move]
    moves_b: List[Move]


class Ledger:
    def __init__(self, agent_names: List[str]):
        self.agent_names = list(agent_names)
        self.matches: List[MatchSummary] = []

    def record(self, summary: MatchSummary):
        self.matches.append(summary)

    # ------------------------------------------------------------- per-agent
    def _moves_of(self, agent: str, partner: Optional[str] = None):
        """Yield (my_move, partner_move, partner_name) for every recorded round of `agent`."""
        for m in self.matches:
            if agent == m.a:
                mine, theirs, other = m.moves_a, m.moves_b, m.b
            elif agent == m.b:
                mine, theirs, other = m.moves_b, m.moves_a, m.a
            else:
                continue
            if partner is not None and other != partner:
                continue
            for x, y in zip(mine, theirs):
                yield x, y, other

    def rounds_played(self, agent: str) -> int:
        return sum(1 for _ in self._moves_of(agent))

    def cooperation_rate(self, agent: str) -> Optional[float]:
        rounds = list(self._moves_of(agent))
        if not rounds:
            return None
        return sum(1 for mine, _, _ in rounds if mine is Move.ALPHA) / len(rounds)

    def betrayals(self, agent: str, exclude_partner: Optional[str] = None) -> int:
        """Rounds where `agent` played Beta against a partner who played Alpha."""
        return sum(
            1 for mine, theirs, other in self._moves_of(agent)
            if mine is Move.BETA and theirs is Move.ALPHA and other != exclude_partner
        )

    def justified_beta(self, agent: str) -> int:
        return sum(1 for mine, theirs, _ in self._moves_of(agent) if mine is Move.BETA and theirs is Move.BETA)

    def reputation(self, agent: str) -> Optional[float]:
        """The single public number: cooperation rate, or None before the agent has played."""
        return self.cooperation_rate(agent)

    def reputation_snapshot(self) -> Dict[str, Optional[float]]:
        return {name: self.reputation(name) for name in self.agent_names}

    # ----------------------------------------------------------------- views
    def score_lines(self, viewer: str, partner: str) -> List[str]:
        """Reputation 'score' view: one line per other agent."""
        lines = []
        for name in self.agent_names:
            if name == viewer:
                continue
            rounds = self.rounds_played(name)
            tag = " (your partner now)" if name == partner else ""
            if rounds == 0:
                lines.append(f"- {name}{tag}: no public record yet")
                continue
            rate = self.cooperation_rate(name)
            lines.append(
                f"- {name}{tag}: played Alpha in {rate:.0%} of {rounds} rounds; "
                f"{self.betrayals(name)} times played Beta against a partner who played Alpha"
            )
        return lines

    def recent_matches_lines(self, agent: str, window: int, viewer: str) -> List[str]:
        """Reputation 'ledger' view: what `agent` did in its last `window` matches (who betrayed whom)."""
        own = [m for m in self.matches if agent in (m.a, m.b)][-window:]
        lines = []
        for m in own:
            mine, theirs, other = (m.moves_a, m.moves_b, m.b) if agent == m.a else (m.moves_b, m.moves_a, m.a)
            who = "you" if other == viewer else other
            note = ""
            if any(x is Move.BETA and y is Move.ALPHA for x, y in zip(mine, theirs)):
                note = f"  <- {agent} played Beta against an Alpha from {who}"
            lines.append(f"- episode {m.episode}, {agent} vs {who}: {agent} {letters(mine)} | {who} {letters(theirs)}{note}")
        return lines
