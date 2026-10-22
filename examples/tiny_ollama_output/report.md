# Run report: talk=every_round+board | reputation=ledger

3 matches, 6 rounds.

## Verdicts

- PASS: no failed LLM calls.
- NOTE: 60% of promises were broken.

## Society

| Metric | Value |
|---|---|
| Cooperation rate (Alpha) | 42% |
| Mutual Alpha rate | 0% |
| Mutual Beta rate | 17% |
| Points per round (all agents) | 2.25 |
| Points per round, LLM agents | 1.38 |
| Points per round, classical agents | 4.00 |
| Inequality (Gini of totals) | 0.27 |
| Cooperation, last round vs earlier | 33% (n=6) vs 50% (n=6) |
| Messages sent (mean length) | 12 (49 chars) |
| Promises (broken) | 10 (60%) |
| Public board posts | 4 |

Cooperation by episode: ep 1: 42%

## Agents

| Agent | Kind | Points | Points/round | Alpha rate | Betrayals | Promises (broken) | Mean trust | Expectation accuracy | Fallback rounds |
|---|---|---|---|---|---|---|---|---|---|
| Eli | classical | 16 | 4.00 | 0% | 3 | 4 (100%) | n/a | n/a | 0 |
| Ada | llm | 6 | 1.50 | 50% | 1 | 3 (33%) | 8.0 | 50% | 0 |
| Bo | llm | 5 | 1.25 | 75% | 1 | 3 (33%) | 8.0 | 25% | 0 |

## Do the LLM agents use what they are shown?

| Question | Answer |
|---|---|
| Alpha rate when the partner promised Alpha | 75% (n=4) |
| Alpha rate when the partner promised Beta | 67% (n=3) |
| Alpha rate when the partner promised nothing | 0% (n=1) |
| Opening move, partner's public cooperation >= 50% | 100% (n=1) |
| Opening move, partner's public cooperation < 50% | 100% (n=1) |
| Opening move, partner never betrayed others | 67% (n=3) |
| Opening move, partner betrayed others before | 100% (n=1) |

The opening-move rows use only the first round of each match, so they reflect public information (and, if chat is on, the opening messages), not the play inside the match. When reputation is off the agents could not see it, so those rows are a control: any gap there is chance or a correlation, not a response.

## LLM call health

`{'calls': 20, 'retries': 0, 'prompt_tokens': 12169, 'completion_tokens': 970}`

Per-agent fallbacks: `{'Ada': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Bo': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}}`
