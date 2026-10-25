# Run report: talk=every_round+board | reputation=ledger

20 matches, 80 rounds.

## Verdicts

- PASS: no failed LLM calls.
- WARN: mutual Beta in 90% of rounds; the society is stuck in the bad equilibrium.
- NOTE: 42% of promises were broken.

## Society

| Metric | Value |
|---|---|
| Cooperation rate (Alpha) | 5% |
| Mutual Alpha rate | 0% |
| Mutual Beta rate | 90% |
| Points per round (all agents) | 1.15 |
| Points per round, LLM agents | 1.25 |
| Points per round, classical agents | 1.00 |
| Inequality (Gini of totals) | 0.07 |
| Cooperation, last round vs earlier | 0% (n=40) vs 7% (n=120) |
| Messages sent (mean length) | 160 (107 chars) |
| Promises (broken) | 139 (42%) |
| Public board posts | 24 |

Cooperation by episode: ep 1: 5%, ep 2: 5%

## Agents

| Agent | Kind | Points | Points/round | Alpha rate | Betrayals | Promises (broken) | Mean trust | Expectation accuracy | Fallback rounds |
|---|---|---|---|---|---|---|---|---|---|
| Ada | llm | 40 | 1.25 | 0% | 2 | 24 (50%) | 4.5 | 88% | 0 |
| Eli | classical | 40 | 1.25 | 0% | 2 | 32 (100%) | n/a | n/a | 0 |
| Cy | llm | 40 | 1.25 | 0% | 2 | 29 (17%) | 3.4 | 94% | 0 |
| Bo | llm | 40 | 1.25 | 0% | 2 | 22 (45%) | 3.7 | 94% | 0 |
| Dee | classical | 24 | 0.75 | 25% | 0 | 32 (0%) | n/a | n/a | 0 |

## Do the LLM agents use what they are shown?

| Question | Answer |
|---|---|
| Alpha rate when the partner promised Alpha | 0% (n=43) |
| Alpha rate when the partner promised Beta | 0% (n=42) |
| Alpha rate when the partner promised nothing | 0% (n=11) |
| Opening move, partner's public cooperation >= 50% | n/a (n=0) |
| Opening move, partner's public cooperation < 50% | 0% (n=20) |
| Opening move, partner never betrayed others | 0% (n=11) |
| Opening move, partner betrayed others before | 0% (n=13) |

The opening-move rows use only the first round of each match, so they reflect public information (and, if chat is on, the opening messages), not the play inside the match. When reputation is off the agents could not see it, so those rows are a control: any gap there is chance or a correlation, not a response.

## LLM call health

`{'calls': 216, 'retries': 0, 'prompt_tokens': 366841, 'completion_tokens': 90495}`

Per-agent fallbacks: `{'Ada': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Bo': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Cy': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}}`
