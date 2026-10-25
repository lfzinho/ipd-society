# Run report: talk=every_round | reputation=none

20 matches, 80 rounds.

## Verdicts

- PASS: no failed LLM calls.
- WARN: mutual Beta in 54% of rounds; the society is stuck in the bad equilibrium.
- NOTE: 39% of promises were broken.
- NOTE: cooperation drops in the last round of matches (end-game defection).

## Society

| Metric | Value |
|---|---|
| Cooperation rate (Alpha) | 38% |
| Mutual Alpha rate | 29% |
| Mutual Beta rate | 54% |
| Points per round (all agents) | 1.84 |
| Points per round, LLM agents | 2.00 |
| Points per round, classical agents | 1.59 |
| Inequality (Gini of totals) | 0.08 |
| Cooperation, last round vs earlier | 10% (n=40) vs 47% (n=120) |
| Messages sent (mean length) | 160 (98 chars) |
| Promises (broken) | 147 (39%) |
| Public board posts | 0 |

Cooperation by episode: ep 1: 38%, ep 2: 38%

## Agents

| Agent | Kind | Points | Points/round | Alpha rate | Betrayals | Promises (broken) | Mean trust | Expectation accuracy | Fallback rounds |
|---|---|---|---|---|---|---|---|---|---|
| Cy | llm | 72 | 2.25 | 47% | 4 | 28 (14%) | 5.0 | 84% | 0 |
| Ada | llm | 62 | 1.94 | 44% | 2 | 27 (30%) | 4.7 | 91% | 0 |
| Bo | llm | 58 | 1.81 | 25% | 4 | 28 (50%) | 4.8 | 78% | 0 |
| Dee | classical | 54 | 1.69 | 72% | 0 | 32 (0%) | n/a | n/a | 0 |
| Eli | classical | 48 | 1.50 | 0% | 4 | 32 (100%) | n/a | n/a | 0 |

## Do the LLM agents use what they are shown?

| Question | Answer |
|---|---|
| Alpha rate when the partner promised Alpha | 48% (n=75) |
| Alpha rate when the partner promised Beta | 0% (n=14) |
| Alpha rate when the partner promised nothing | 14% (n=7) |
| Opening move, partner's public cooperation >= 50% | 88% (n=8) |
| Opening move, partner's public cooperation < 50% | 58% (n=12) |
| Opening move, partner never betrayed others | 83% (n=12) |
| Opening move, partner betrayed others before | 50% (n=12) |

The opening-move rows use only the first round of each match, so they reflect public information (and, if chat is on, the opening messages), not the play inside the match. When reputation is off the agents could not see it, so those rows are a control: any gap there is chance or a correlation, not a response.

## LLM call health

`{'calls': 216, 'retries': 0, 'prompt_tokens': 202814, 'completion_tokens': 97714}`

Per-agent fallbacks: `{'Ada': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Bo': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Cy': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}}`
