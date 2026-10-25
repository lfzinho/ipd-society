# Run report: talk=none | reputation=ledger

20 matches, 80 rounds.

## Verdicts

- PASS: no failed LLM calls.
- WARN: mutual Beta in 80% of rounds; the society is stuck in the bad equilibrium.

## Society

| Metric | Value |
|---|---|
| Cooperation rate (Alpha) | 13% |
| Mutual Alpha rate | 6% |
| Mutual Beta rate | 80% |
| Points per round (all agents) | 1.33 |
| Points per round, LLM agents | 1.45 |
| Points per round, classical agents | 1.16 |
| Inequality (Gini of totals) | 0.07 |
| Cooperation, last round vs earlier | 2% (n=40) vs 17% (n=120) |
| Messages sent (mean length) | 0 (n/a chars) |
| Promises (broken) | 0 (n/a) |
| Public board posts | 0 |

Cooperation by episode: ep 1: 21%, ep 2: 5%

## Agents

| Agent | Kind | Points | Points/round | Alpha rate | Betrayals | Promises (broken) | Mean trust | Expectation accuracy | Fallback rounds |
|---|---|---|---|---|---|---|---|---|---|
| Cy | llm | 48 | 1.50 | 22% | 2 | 0 (n/a) | 6.2 | 94% | 0 |
| Ada | llm | 47 | 1.47 | 9% | 3 | 0 (n/a) | 5.8 | 94% | 0 |
| Bo | llm | 44 | 1.38 | 0% | 3 | 0 (n/a) | 6.7 | 88% | 0 |
| Eli | classical | 44 | 1.38 | 0% | 3 | 0 (n/a) | n/a | n/a | 0 |
| Dee | classical | 30 | 0.94 | 34% | 0 | 0 (n/a) | n/a | n/a | 0 |

## Do the LLM agents use what they are shown?

| Question | Answer |
|---|---|
| Alpha rate when the partner promised Alpha | n/a (n=0) |
| Alpha rate when the partner promised Beta | n/a (n=0) |
| Alpha rate when the partner promised nothing | 10% (n=96) |
| Opening move, partner's public cooperation >= 50% | 0% (n=4) |
| Opening move, partner's public cooperation < 50% | 0% (n=15) |
| Opening move, partner never betrayed others | 50% (n=10) |
| Opening move, partner betrayed others before | 0% (n=14) |

The opening-move rows use only the first round of each match, so they reflect public information (and, if chat is on, the opening messages), not the play inside the match. When reputation is off the agents could not see it, so those rows are a control: any gap there is chance or a correlation, not a response.

## LLM call health

`{'calls': 120, 'retries': 0, 'prompt_tokens': 141993, 'completion_tokens': 45298}`

Per-agent fallbacks: `{'Ada': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Bo': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Cy': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}}`
