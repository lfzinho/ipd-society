# Run report: talk=every_round+board | reputation=ledger

20 matches, 80 rounds.

## Verdicts

- PASS: no failed LLM calls.
- NOTE: 35% of promises were broken.
- NOTE: cooperation drops in the last round of matches (end-game defection).

## Society

| Metric | Value |
|---|---|
| Cooperation rate (Alpha) | 42% |
| Mutual Alpha rate | 35% |
| Mutual Beta rate | 50% |
| Points per round (all agents) | 1.93 |
| Points per round, LLM agents | 2.19 |
| Points per round, classical agents | 1.53 |
| Inequality (Gini of totals) | 0.10 |
| Cooperation, last round vs earlier | 8% (n=40) vs 54% (n=120) |
| Messages sent (mean length) | 160 (101 chars) |
| Promises (broken) | 156 (35%) |
| Public board posts | 24 |

Cooperation by episode: ep 1: 45%, ep 2: 40%

## Agents

| Agent | Kind | Points | Points/round | Alpha rate | Betrayals | Promises (broken) | Mean trust | Expectation accuracy | Fallback rounds |
|---|---|---|---|---|---|---|---|---|---|
| Ada | llm | 73 | 2.28 | 50% | 3 | 32 (25%) | 4.9 | 88% | 0 |
| Bo | llm | 71 | 2.22 | 47% | 3 | 29 (21%) | 4.7 | 88% | 0 |
| Cy | llm | 66 | 2.06 | 44% | 3 | 31 (26%) | 4.5 | 88% | 0 |
| Dee | classical | 54 | 1.69 | 72% | 0 | 32 (0%) | n/a | n/a | 0 |
| Eli | classical | 44 | 1.38 | 0% | 3 | 32 (100%) | n/a | n/a | 0 |

## Do the LLM agents use what they are shown?

| Question | Answer |
|---|---|
| Alpha rate when the partner promised Alpha | 54% (n=84) |
| Alpha rate when the partner promised Beta | 0% (n=11) |
| Alpha rate when the partner promised nothing | 0% (n=1) |
| Opening move, partner's public cooperation >= 50% | 100% (n=12) |
| Opening move, partner's public cooperation < 50% | 29% (n=7) |
| Opening move, partner never betrayed others | 100% (n=11) |
| Opening move, partner betrayed others before | 62% (n=13) |

The opening-move rows use only the first round of each match, so they reflect public information (and, if chat is on, the opening messages), not the play inside the match. When reputation is off the agents could not see it, so those rows are a control: any gap there is chance or a correlation, not a response.

## LLM call health

`{'calls': 198, 'retries': 0, 'prompt_tokens': 361270, 'completion_tokens': 91639}`

Per-agent fallbacks: `{'Ada': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Bo': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Cy': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}}`
