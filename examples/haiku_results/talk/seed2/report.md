# Run report: talk=every_round | reputation=none

20 matches, 80 rounds.

## Verdicts

- PASS: no failed LLM calls.
- NOTE: 32% of promises were broken.
- NOTE: cooperation drops in the last round of matches (end-game defection).

## Society

| Metric | Value |
|---|---|
| Cooperation rate (Alpha) | 41% |
| Mutual Alpha rate | 32% |
| Mutual Beta rate | 50% |
| Points per round (all agents) | 1.91 |
| Points per round, LLM agents | 2.19 |
| Points per round, classical agents | 1.50 |
| Inequality (Gini of totals) | 0.10 |
| Cooperation, last round vs earlier | 8% (n=40) vs 52% (n=120) |
| Messages sent (mean length) | 160 (97 chars) |
| Promises (broken) | 147 (32%) |
| Public board posts | 0 |

Cooperation by episode: ep 1: 44%, ep 2: 39%

## Agents

| Agent | Kind | Points | Points/round | Alpha rate | Betrayals | Promises (broken) | Mean trust | Expectation accuracy | Fallback rounds |
|---|---|---|---|---|---|---|---|---|---|
| Cy | llm | 76 | 2.38 | 59% | 3 | 28 (7%) | 5.4 | 94% | 0 |
| Ada | llm | 68 | 2.12 | 47% | 3 | 30 (23%) | 4.6 | 91% | 0 |
| Bo | llm | 66 | 2.06 | 38% | 4 | 25 (24%) | 4.8 | 94% | 0 |
| Dee | classical | 48 | 1.50 | 62% | 0 | 32 (0%) | n/a | n/a | 0 |
| Eli | classical | 48 | 1.50 | 0% | 4 | 32 (100%) | n/a | n/a | 0 |

## Do the LLM agents use what they are shown?

| Question | Answer |
|---|---|
| Alpha rate when the partner promised Alpha | 59% (n=78) |
| Alpha rate when the partner promised Beta | 0% (n=14) |
| Alpha rate when the partner promised nothing | 0% (n=4) |
| Opening move, partner's public cooperation >= 50% | 100% (n=11) |
| Opening move, partner's public cooperation < 50% | 50% (n=8) |
| Opening move, partner never betrayed others | 100% (n=11) |
| Opening move, partner betrayed others before | 69% (n=13) |

The opening-move rows use only the first round of each match, so they reflect public information (and, if chat is on, the opening messages), not the play inside the match. When reputation is off the agents could not see it, so those rows are a control: any gap there is chance or a correlation, not a response.

## LLM call health

`{'calls': 216, 'retries': 0, 'prompt_tokens': 205137, 'completion_tokens': 97924}`

Per-agent fallbacks: `{'Ada': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Bo': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Cy': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}}`
