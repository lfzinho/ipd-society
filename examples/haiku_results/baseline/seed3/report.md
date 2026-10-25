# Run report: talk=none | reputation=none

20 matches, 80 rounds.

## Verdicts

- PASS: no failed LLM calls.
- WARN: mutual Beta in 59% of rounds; the society is stuck in the bad equilibrium.
- NOTE: cooperation drops in the last round of matches (end-game defection).

## Society

| Metric | Value |
|---|---|
| Cooperation rate (Alpha) | 33% |
| Mutual Alpha rate | 25% |
| Mutual Beta rate | 59% |
| Points per round (all agents) | 1.74 |
| Points per round, LLM agents | 1.91 |
| Points per round, classical agents | 1.50 |
| Inequality (Gini of totals) | 0.09 |
| Cooperation, last round vs earlier | 5% (n=40) vs 42% (n=120) |
| Messages sent (mean length) | 0 (n/a chars) |
| Promises (broken) | 0 (n/a) |
| Public board posts | 0 |

Cooperation by episode: ep 1: 39%, ep 2: 28%

## Agents

| Agent | Kind | Points | Points/round | Alpha rate | Betrayals | Promises (broken) | Mean trust | Expectation accuracy | Fallback rounds |
|---|---|---|---|---|---|---|---|---|---|
| Cy | llm | 73 | 2.28 | 50% | 3 | 0 (n/a) | 6.2 | 78% | 0 |
| Bo | llm | 57 | 1.78 | 25% | 3 | 0 (n/a) | 6.0 | 81% | 0 |
| Ada | llm | 53 | 1.66 | 34% | 2 | 0 (n/a) | 6.4 | 84% | 0 |
| Eli | classical | 52 | 1.62 | 0% | 5 | 0 (n/a) | n/a | n/a | 0 |
| Dee | classical | 44 | 1.38 | 56% | 0 | 0 (n/a) | n/a | n/a | 0 |

## Do the LLM agents use what they are shown?

| Question | Answer |
|---|---|
| Alpha rate when the partner promised Alpha | n/a (n=0) |
| Alpha rate when the partner promised Beta | n/a (n=0) |
| Alpha rate when the partner promised nothing | 36% (n=96) |
| Opening move, partner's public cooperation >= 50% | 64% (n=11) |
| Opening move, partner's public cooperation < 50% | 56% (n=9) |
| Opening move, partner never betrayed others | 78% (n=9) |
| Opening move, partner betrayed others before | 60% (n=15) |

The opening-move rows use only the first round of each match, so they reflect public information (and, if chat is on, the opening messages), not the play inside the match. When reputation is off the agents could not see it, so those rows are a control: any gap there is chance or a correlation, not a response.

## LLM call health

`{'calls': 120, 'retries': 0, 'prompt_tokens': 103525, 'completion_tokens': 47587}`

Per-agent fallbacks: `{'Ada': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Bo': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Cy': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}}`
