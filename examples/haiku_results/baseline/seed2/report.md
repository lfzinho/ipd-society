# Run report: talk=none | reputation=none

20 matches, 80 rounds.

## Verdicts

- PASS: no failed LLM calls.
- WARN: mutual Beta in 65% of rounds; the society is stuck in the bad equilibrium.
- NOTE: cooperation drops in the last round of matches (end-game defection).

## Society

| Metric | Value |
|---|---|
| Cooperation rate (Alpha) | 26% |
| Mutual Alpha rate | 16% |
| Mutual Beta rate | 65% |
| Points per round (all agents) | 1.61 |
| Points per round, LLM agents | 1.82 |
| Points per round, classical agents | 1.28 |
| Inequality (Gini of totals) | 0.10 |
| Cooperation, last round vs earlier | 2% (n=40) vs 33% (n=120) |
| Messages sent (mean length) | 0 (n/a chars) |
| Promises (broken) | 0 (n/a) |
| Public board posts | 0 |

Cooperation by episode: ep 1: 32%, ep 2: 19%

## Agents

| Agent | Kind | Points | Points/round | Alpha rate | Betrayals | Promises (broken) | Mean trust | Expectation accuracy | Fallback rounds |
|---|---|---|---|---|---|---|---|---|---|
| Ada | llm | 65 | 2.03 | 25% | 5 | 0 (n/a) | 5.6 | 94% | 0 |
| Cy | llm | 57 | 1.78 | 28% | 4 | 0 (n/a) | 5.4 | 78% | 0 |
| Bo | llm | 53 | 1.66 | 28% | 3 | 0 (n/a) | 6.1 | 81% | 0 |
| Eli | classical | 44 | 1.38 | 0% | 3 | 0 (n/a) | n/a | n/a | 0 |
| Dee | classical | 38 | 1.19 | 47% | 0 | 0 (n/a) | n/a | n/a | 0 |

## Do the LLM agents use what they are shown?

| Question | Answer |
|---|---|
| Alpha rate when the partner promised Alpha | n/a (n=0) |
| Alpha rate when the partner promised Beta | n/a (n=0) |
| Alpha rate when the partner promised nothing | 27% (n=96) |
| Opening move, partner's public cooperation >= 50% | 75% (n=4) |
| Opening move, partner's public cooperation < 50% | 40% (n=15) |
| Opening move, partner never betrayed others | 82% (n=11) |
| Opening move, partner betrayed others before | 38% (n=13) |

The opening-move rows use only the first round of each match, so they reflect public information (and, if chat is on, the opening messages), not the play inside the match. When reputation is off the agents could not see it, so those rows are a control: any gap there is chance or a correlation, not a response.

## LLM call health

`{'calls': 120, 'retries': 0, 'prompt_tokens': 105037, 'completion_tokens': 50777}`

Per-agent fallbacks: `{'Ada': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Bo': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Cy': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}}`
