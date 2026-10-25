# Run report: talk=every_round+board | reputation=ledger

20 matches, 80 rounds.

## Verdicts

- PASS: no failed LLM calls.
- WARN: mutual Beta in 69% of rounds; the society is stuck in the bad equilibrium.
- NOTE: 34% of promises were broken.
- NOTE: cooperation drops in the last round of matches (end-game defection).

## Society

| Metric | Value |
|---|---|
| Cooperation rate (Alpha) | 23% |
| Mutual Alpha rate | 15% |
| Mutual Beta rate | 69% |
| Points per round (all agents) | 1.54 |
| Points per round, LLM agents | 1.86 |
| Points per round, classical agents | 1.06 |
| Inequality (Gini of totals) | 0.15 |
| Cooperation, last round vs earlier | 2% (n=40) vs 30% (n=120) |
| Messages sent (mean length) | 160 (107 chars) |
| Promises (broken) | 147 (34%) |
| Public board posts | 24 |

Cooperation by episode: ep 1: 29%, ep 2: 18%

## Agents

| Agent | Kind | Points | Points/round | Alpha rate | Betrayals | Promises (broken) | Mean trust | Expectation accuracy | Fallback rounds |
|---|---|---|---|---|---|---|---|---|---|
| Ada | llm | 63 | 1.97 | 34% | 3 | 30 (20%) | 4.1 | 94% | 0 |
| Cy | llm | 59 | 1.84 | 28% | 3 | 26 (23%) | 3.5 | 91% | 0 |
| Bo | llm | 57 | 1.78 | 28% | 4 | 27 (22%) | 4.2 | 78% | 0 |
| Eli | classical | 44 | 1.38 | 0% | 3 | 32 (100%) | n/a | n/a | 0 |
| Dee | classical | 24 | 0.75 | 25% | 0 | 32 (0%) | n/a | n/a | 0 |

## Do the LLM agents use what they are shown?

| Question | Answer |
|---|---|
| Alpha rate when the partner promised Alpha | 46% (n=63) |
| Alpha rate when the partner promised Beta | 0% (n=29) |
| Alpha rate when the partner promised nothing | 0% (n=4) |
| Opening move, partner's public cooperation >= 50% | 100% (n=1) |
| Opening move, partner's public cooperation < 50% | 37% (n=19) |
| Opening move, partner never betrayed others | 45% (n=11) |
| Opening move, partner betrayed others before | 54% (n=13) |

The opening-move rows use only the first round of each match, so they reflect public information (and, if chat is on, the opening messages), not the play inside the match. When reputation is off the agents could not see it, so those rows are a control: any gap there is chance or a correlation, not a response.

## LLM call health

`{'calls': 216, 'retries': 0, 'prompt_tokens': 374938, 'completion_tokens': 101192}`

Per-agent fallbacks: `{'Ada': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Bo': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}, 'Cy': {'fallback_messages': 0, 'fallback_moves': 0, 'failed_reflections': 0}}`
