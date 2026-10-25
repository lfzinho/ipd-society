# Run report: talk=none | reputation=ledger

20 matches, 80 rounds.

## Verdicts

- PASS: no failed LLM calls.
- WARN: mutual Beta in 86% of rounds; the society is stuck in the bad equilibrium.

## Society

| Metric | Value |
|---|---|
| Cooperation rate (Alpha) | 8% |
| Mutual Alpha rate | 1% |
| Mutual Beta rate | 86% |
| Points per round (all agents) | 1.21 |
| Points per round, LLM agents | 1.29 |
| Points per round, classical agents | 1.09 |
| Inequality (Gini of totals) | 0.08 |
| Cooperation, last round vs earlier | 0% (n=40) vs 10% (n=120) |
| Messages sent (mean length) | 0 (n/a chars) |
| Promises (broken) | 0 (n/a) |
| Public board posts | 0 |

Cooperation by episode: ep 1: 10%, ep 2: 5%

## Agents

| Agent | Kind | Points | Points/round | Alpha rate | Betrayals | Promises (broken) | Mean trust | Expectation accuracy | Fallback rounds |
|---|---|---|---|---|---|---|---|---|---|
| Eli | classical | 44 | 1.38 | 0% | 3 | 0 (n/a) | n/a | n/a | 0 |
| Cy | llm | 44 | 1.38 | 0% | 3 | 0 (n/a) | 6.9 | 91% | 0 |
| Ada | llm | 40 | 1.25 | 9% | 2 | 0 (n/a) | 7.0 | 91% | 0 |
| Bo | llm | 40 | 1.25 | 0% | 2 | 0 (n/a) | 7.1 | 100% | 0 |
| Dee | classical | 26 | 0.81 | 28% | 0 | 0 (n/a) | n/a | n/a | 0 |

## Do the LLM agents use what they are shown?

| Question | Answer |
|---|---|
| Alpha rate when the partner promised Alpha | n/a (n=0) |
| Alpha rate when the partner promised Beta | n/a (n=0) |
| Alpha rate when the partner promised nothing | 3% (n=96) |
| Opening move, partner's public cooperation >= 50% | 0% (n=1) |
| Opening move, partner's public cooperation < 50% | 0% (n=19) |
| Opening move, partner never betrayed others | 33% (n=9) |
| Opening move, partner betrayed others before | 0% (n=15) |

The opening-move rows use only the first round of each match, so they reflect public information (and, if chat is on, the opening messages), not the play inside the match. When reputation is off the agents could not see it, so those rows are a control: any gap there is chance or a correlation, not a response.

## LLM call health

`{'calls': 120, 'retries': 0, 'prompt_tokens': 144585, 'completion_tokens': 40303}`

Per-agent fallbacks: `{'Ada': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Bo': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Cy': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}}`
