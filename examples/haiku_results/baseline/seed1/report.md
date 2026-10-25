# Run report: talk=none | reputation=none

20 matches, 80 rounds.

## Verdicts

- PASS: no failed LLM calls.
- WARN: mutual Beta in 82% of rounds; the society is stuck in the bad equilibrium.

## Society

| Metric | Value |
|---|---|
| Cooperation rate (Alpha) | 12% |
| Mutual Alpha rate | 6% |
| Mutual Beta rate | 82% |
| Points per round (all agents) | 1.29 |
| Points per round, LLM agents | 1.41 |
| Points per round, classical agents | 1.12 |
| Inequality (Gini of totals) | 0.08 |
| Cooperation, last round vs earlier | 2% (n=40) vs 15% (n=120) |
| Messages sent (mean length) | 0 (n/a chars) |
| Promises (broken) | 0 (n/a) |
| Public board posts | 0 |

Cooperation by episode: ep 1: 16%, ep 2: 8%

## Agents

| Agent | Kind | Points | Points/round | Alpha rate | Betrayals | Promises (broken) | Mean trust | Expectation accuracy | Fallback rounds |
|---|---|---|---|---|---|---|---|---|---|
| Cy | llm | 49 | 1.53 | 19% | 2 | 0 (n/a) | 6.3 | 94% | 0 |
| Bo | llm | 46 | 1.44 | 3% | 3 | 0 (n/a) | 6.6 | 84% | 0 |
| Eli | classical | 40 | 1.25 | 0% | 2 | 0 (n/a) | n/a | n/a | 0 |
| Ada | llm | 40 | 1.25 | 0% | 2 | 0 (n/a) | 6.5 | 97% | 0 |
| Dee | classical | 32 | 1.00 | 38% | 0 | 0 (n/a) | n/a | n/a | 0 |

## Do the LLM agents use what they are shown?

| Question | Answer |
|---|---|
| Alpha rate when the partner promised Alpha | n/a (n=0) |
| Alpha rate when the partner promised Beta | n/a (n=0) |
| Alpha rate when the partner promised nothing | 7% (n=96) |
| Opening move, partner's public cooperation >= 50% | 0% (n=1) |
| Opening move, partner's public cooperation < 50% | 11% (n=19) |
| Opening move, partner never betrayed others | 33% (n=12) |
| Opening move, partner betrayed others before | 0% (n=12) |

The opening-move rows use only the first round of each match, so they reflect public information (and, if chat is on, the opening messages), not the play inside the match. When reputation is off the agents could not see it, so those rows are a control: any gap there is chance or a correlation, not a response.

## LLM call health

`{'calls': 120, 'retries': 0, 'prompt_tokens': 107043, 'completion_tokens': 44514}`

Per-agent fallbacks: `{'Ada': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Bo': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Cy': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}}`
