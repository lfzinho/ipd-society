# Run report: talk=every_round | reputation=none

20 matches, 80 rounds.

## Verdicts

- PASS: no failed LLM calls.
- NOTE: 36% of promises were broken.
- NOTE: cooperation drops in the last round of matches (end-game defection).

## Society

| Metric | Value |
|---|---|
| Cooperation rate (Alpha) | 44% |
| Mutual Alpha rate | 35% |
| Mutual Beta rate | 46% |
| Points per round (all agents) | 1.98 |
| Points per round, LLM agents | 2.18 |
| Points per round, classical agents | 1.69 |
| Inequality (Gini of totals) | 0.08 |
| Cooperation, last round vs earlier | 15% (n=40) vs 54% (n=120) |
| Messages sent (mean length) | 160 (97 chars) |
| Promises (broken) | 142 (36%) |
| Public board posts | 0 |

Cooperation by episode: ep 1: 50%, ep 2: 39%

## Agents

| Agent | Kind | Points | Points/round | Alpha rate | Betrayals | Promises (broken) | Mean trust | Expectation accuracy | Fallback rounds |
|---|---|---|---|---|---|---|---|---|---|
| Cy | llm | 77 | 2.41 | 56% | 3 | 25 (12%) | 5.1 | 97% | 0 |
| Bo | llm | 67 | 2.09 | 44% | 4 | 27 (30%) | 4.9 | 78% | 0 |
| Ada | llm | 65 | 2.03 | 47% | 3 | 26 (31%) | 5.0 | 81% | 0 |
| Dee | classical | 56 | 1.75 | 75% | 0 | 32 (0%) | n/a | n/a | 0 |
| Eli | classical | 52 | 1.62 | 0% | 5 | 32 (100%) | n/a | n/a | 0 |

## Do the LLM agents use what they are shown?

| Question | Answer |
|---|---|
| Alpha rate when the partner promised Alpha | 55% (n=85) |
| Alpha rate when the partner promised Beta | 0% (n=6) |
| Alpha rate when the partner promised nothing | 0% (n=5) |
| Opening move, partner's public cooperation >= 50% | 75% (n=12) |
| Opening move, partner's public cooperation < 50% | 62% (n=8) |
| Opening move, partner never betrayed others | 100% (n=10) |
| Opening move, partner betrayed others before | 57% (n=14) |

The opening-move rows use only the first round of each match, so they reflect public information (and, if chat is on, the opening messages), not the play inside the match. When reputation is off the agents could not see it, so those rows are a control: any gap there is chance or a correlation, not a response.

## LLM call health

`{'calls': 198, 'retries': 0, 'prompt_tokens': 192462, 'completion_tokens': 79718}`

Per-agent fallbacks: `{'Ada': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Bo': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Cy': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}}`
