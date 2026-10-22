# ipd-society

LLM agents in a **repeated social dilemma with communication and reputation**.

This is Steps 2 and 3 of a three-step research project (the full plan is in
`../bold-bardeen/docs/research/research-overview.md`):

| Step | Question | Where |
|---|---|---|
| 1 | One LLM agent against fixed classical strategies. How well does it play, and how does the information it is given matter? | `../bold-bardeen` (done) |
| 2 | Several LLM agents play each other and can **talk** before each move. Does talk change cooperation? Do agents lie, and do they believe each other? | this project, `communication` settings |
| 3 | The same population with a **public record** of who did what to whom, and an optional public board for gossip. Does reputation change who cooperates with whom? | this project, `reputation` settings |

Everything runs offline with a built-in mock model (free, instant, used by the tests). Real models run
through Ollama (local) or OpenRouter (paid API). **No long runs have been done**; see
[Validation](#validation-and-what-it-does-not-show) for exactly what has and has not been tested.

---

## Quick start

```powershell
pip install -r requirements.txt        # axelrod, openai, pydantic, python-dotenv, pytest

pytest                                 # 55 tests, ~15 s, no network
python main.py                         # one offline run with the mock model (config.toml)
python main.py --conditions all        # the four-condition comparison, offline
python main.py --show-prompt move --communication every_round --reputation ledger --board
```

A small real-model run (local Ollama, a few minutes, no cost):

```powershell
python main.py --provider ollama --model qwen2.5:3b --episodes 1 --rounds 2 --communication every_round --reputation ledger --board
```

A ready-made 3-agent config for this is `examples/tiny_ollama.toml` (`python main.py --config examples/tiny_ollama.toml`); its saved output, including the
`trace.jsonl` of the real model's replies, is in `examples/tiny_ollama_output/`.

OpenRouter needs `OPENROUTER_API_KEY` in the environment or a `.env` file. Start with `--episodes 1 --rounds 2` and
look at `output/report.md` before scaling up; the number of LLM calls is given [below](#cost-and-run-size).

---

## The game

`N` agents. Each *episode* is a full round-robin: every pair plays one **match** of `rounds_per_match` rounds.
A run is `episodes` episodes. In every round the two partners pick **Alpha** (cooperate) or **Beta** (defect) at
the same time:

| | partner Alpha | partner Beta |
|---|---|---|
| **I play Alpha** | 3 / 3 | 0 / 5 |
| **I play Beta** | 5 / 0 | 1 / 1 |

The labels are neutral on purpose (Step 1 showed why the word "Prisoner's Dilemma" pulls models towards
memorised behaviour). Agents are told how many rounds and episodes there are, and that they will meet the same
agents again, so cooperation is rational but defection always pays in a single round.

**Population.** Set in `config.toml` under `[[agents]]`. Two kinds:

* `kind = "llm"`: a language model. Optional `persona` text is appended to its instructions, and optional
  `model` overrides the default so one society can mix models.
* `kind = "classical"`: an [Axelrod](https://axelrod.readthedocs.io) strategy (`strategy = "TitForTat"`,
  `"Defector"`, `"Grudger"`, ...; the Step 1 names such as `AlwaysDefect` also work). Its `talk` is `silent`,
  `honest` (promises the move it is about to make) or `deceptive` (always promises Alpha, plays its strategy).
  A deceptive Defector is the standard test of whether talk is believed.

---

## The three variables (what you switch between conditions)

### Communication (`[communication]`, Step 2)

| `mode` | When partners can message each other |
|---|---|
| `none` | never (Step 1 behaviour) |
| `pre_match` | once, before round 1 of each match |
| `every_round` | before every round |

`exchanges` is how many message swaps happen before the moves. Within one exchange both agents write
**simultaneously** (neither sees the other's new message), then both read. With `exchanges = 2` they can reply.
Messages are *cheap talk*: nothing is enforced. Every message comes with a structured `promise`
(`Alpha`, `Beta` or `none`), which lets the harness measure honesty exactly, without reading free text.

### Reputation (`[reputation]`, Step 3)

| `mode` | What every agent can see about its partner |
|---|---|
| `none` | nothing beyond the current match and its own memory |
| `score` | a scoreboard: each agent's Alpha rate and how often it played Beta against a partner who played Alpha |
| `ledger` | the scoreboard plus the partner's last `window` matches round by round, with betrayals marked |

The record is **verifiable**: it is built from what actually happened (`society/ledger.py`), not from what agents
say. That is the key difference from the next variable.

### Public board (`public_board`, Step 3)

After each match an agent may post one public statement, up to `board_size` recent statements are shown to everyone.
This is **gossip**: it can be true, false or self-serving. Comparing `ledger` (verifiable) with `board` (unverifiable)
tests whether LLM agents tell the difference.

### The four standard conditions

`python main.py --conditions all` runs the same agents and seed under each:

| Name | communication | reputation | board |
|---|---|---|---|
| `baseline` | none | none | off |
| `talk` | every_round | none | off |
| `watch` | none | ledger | off |
| `talk_watch` | every_round | ledger | on |

`--seeds 1,2,3` repeats each condition per seed and reports mean ± standard deviation (one seed shows nothing about
noise; always use several for a claim).

---

## What an agent sees (and nothing else)

Prompts are assembled in `society/prompts.py` from the text in **`prompts.toml`** (all wording lives there; edit
that file, not Python). The prompt is: intro blocks, then a situation, then a task.

* **Intro**: rules and payoffs, the goal ("as many points as possible, only your own total counts"), the structure
  (rounds, episodes, repeated meetings), then exactly one communication block and one reputation block matching the
  current condition, plus the board block if it is on, plus the agent's `persona`.
* **Situation** (facts supplied by the harness): episode, round, the match history and scores so far, retrieved
  memories, the public record lines (only if reputation is on), recent board posts (only if the board is on), and the
  messages of this round.
* **Task**: reply with JSON only. A *message* call returns `{message, promise}`; a *move* call returns
  `{decision, expected_partner, trust, reasoning}`; a *reflection* call (after each match) returns
  `{partner_assessment, lesson, importance, public_statement}`.

`expected_partner` and `trust` exist for measurement: they show whether the agent believed the promise and whether
its prediction was right. Run `python main.py --show-prompt message|move|reflection` (with the condition flags) to
print an exact prompt. Unknown placeholders or missing blocks in `prompts.toml` fail at load.

**Memory** (`society/memory.py`, after Park et al. 2023, without embeddings). After each match an agent stores an
*observation* (the harness-measured summary: moves, scores, promises made and kept) and then a *reflection* (its own
lesson, rated 1-10, linked to the observation). Each prompt retrieves the top `memory.top_k` entries by
recency + importance + relevance (tagged by partner). Near-duplicate lessons are merged, so one repeated lesson
cannot crowd out the rest (a failure seen in Step 1).

---

## How a round works

`society/world.py` runs, for every match:

```
begin_match
for each round:
    message phase   (if talking is on this round): `exchanges` swaps, both agents write, then both read
    move phase      both agents choose; each sees the messages of this round
    noise           each executed move may be flipped with probability config.world.noise
    observe         both agents see the executed moves (their intended moves are logged separately)
after the match:
    the ledger is updated, each agent stores an observation, reflects, and may post to the board
    the match record is appended to matches.jsonl and state.json is saved
```

`intended` (what the agent chose) and `executed` (after noise) are both recorded, so noise can be separated from
deception.

---

## Code map

| File | Role |
|---|---|
| `main.py` | CLI: single run, `--conditions`, `--seeds`, `--show-prompt`, overrides. Exit code 2 on an LLM outage. |
| `config.toml` | Experiment settings and the agent list (strict: typos fail at load). |
| `prompts.toml` | All prompt text. |
| `society/config.py` | Pydantic models for the config. |
| `society/game.py` | `Move` (Alpha/Beta) and the payoff table. |
| `society/world.py` | `Society`: schedule, match loop, noise, ledger, board, checkpoint and resume. |
| `society/agents.py` | `ScriptedAgent` (Axelrod strategy, optionally chatty) and `LLMAgent` (prompts, memory, fallback). |
| `society/llm.py` | `LLMClient` (providers, JSON parsing, retries, trace) and `FallbackGuard` (aborts on repeated failures). |
| `society/prompts.py` | Assembles prompts from `prompts.toml`. |
| `society/schemas.py` | What each LLM reply must contain; tolerant parsing. |
| `society/ledger.py` | The public record and the views derived from it. |
| `society/memory.py` | Memory stream (observation, reflection, retrieval). |
| `society/metrics.py` | All measurements, computed from finished matches. |
| `society/report.py` | Markdown reports, verdicts, comparison tables. |
| `society/mock.py` | Offline stand-in model used by the tests. |
| `society/trace.py` | `trace.jsonl` writer. |
| `tests/` | 55 offline tests. |
| `examples/` | A tiny real-model config and its saved output. |

---

## Output files

For a run written to `output/` (or `output/<condition>[/seed<k>]/` with `--conditions`):

| File | Contents |
|---|---|
| `report.md` | Verdicts, society metrics, per-agent table, "do agents use what they are shown?" table. Read this first. |
| `metrics.json` | The same numbers, machine-readable. |
| `matches.jsonl` | One record per match: every round's messages, promises, intended and executed moves, expectations, trust, payoffs, plus the reputation snapshot at match start. The raw dataset. |
| `trace.jsonl` | One record per LLM call: prompt, raw reply, parsed reply, attempts, errors, tokens. Open it when something looks wrong. |
| `state.json` | Resume state (memories, board, finished match ids). |
| `comparison.md` | With `--conditions`: one row per condition. |

---

## Metrics (what they mean and why)

All computed from `matches.jsonl` in `society/metrics.py`.

* **Cooperation rate, mutual Alpha rate, mutual Beta rate**: the headline. Mutual Beta above 50% triggers a warning
  (the society is stuck in the bad equilibrium).
* **Points per round** (all, LLM agents, classical agents): 3.0 is permanent mutual Alpha, 1.0 permanent mutual Beta.
  Comparing LLM with classical agents shows who gains from the society.
* **Gini of totals**: inequality; high values mean some agents exploit others.
* **Cooperation by episode**: learning or collapse over time.
* **End game**: Alpha rate in the last round of a match against earlier rounds (backward-induction defection).
* **Promises and deception**: a promise is *broken* when the executed move differs from the promised one. Per-agent
  deception rate shows who lies (a deceptive scripted agent is 100% by construction, a good check).
* **Cooperation after a promise**: among LLM agents, P(Alpha | partner promised Alpha / Beta / nothing). Do words move
  behaviour?
* **Mean trust and expectation accuracy**: how much the agent said it believed its partner, and how often its
  predicted partner move was right.
* **Opening move by public reputation / by third-party betrayal**: only the **first round** of each match, so the
  decision cannot depend on the match itself. Compares the Alpha rate against partners with a good (>= 50%) vs bad
  public record, and against partners who did or did not betray *other* agents before. This isolates
  reputation-based and third-party responses. With reputation off the same rows are a **control**: agents could
  not see the record, so a gap there is not a response.
* **Call health and fallbacks**: failed calls, retries, parse failures and the number of agent-rounds that were played
  by the neutral fallback (Alpha first, then copy the partner's last move). A `FAIL` verdict means the results mix
  model play with fallback play.

---

## Observability and recovery

Learned from Step 1 (a long run failed and the cause was unknowable):

* Every LLM call is written to `trace.jsonl` with its prompt, raw reply, and errors.
* Failed calls are retried (`llm.max_retries`), then replaced by a neutral fallback that is **counted and shown in
  the report**, never hidden.
* After `llm.max_consecutive_fallbacks` failures in a row the run stops with exit code 2 and a message. Nothing is
  lost: rerun the same command and it resumes after the last finished match (memories and board included).
  Resumed results are identical to an uninterrupted run (tested).
* `state.json` stores a fingerprint of the config; resuming with a changed config starts over with a warning.

---

## Cost and run size

LLM calls per run ≈ `matches × rounds × (moves + messages) + reflections`, where for two LLM agents in a match:

* moves: 2 per round,
* messages: 2 × `exchanges` per round (if `every_round`),
* reflections: 2 per match.

Measured on the shipped `config.toml` (5 agents, 3 of them LLM; 3 episodes of 10 matches; 5 rounds per match):
**216 LLM calls with communication off, 396 with `every_round`** (one exchange). The local run below averaged about 600
prompt tokens and 50 completion tokens per call, so a full shipped-config run is roughly 130k-240k prompt tokens. A
society of only LLM agents grows quickly: calls scale with the number of pairs, which is `N(N-1)/2` per episode.
Estimate first, then run one episode with 2 rounds.

---

## Validation and what it does not show

**Tested (offline, `pytest`, 55 tests):**

* configuration is strict, prompts render in all 9 communication × reputation combinations without stray
  placeholders, and each information channel appears only when enabled;
* the ledger's rates, betrayal counts and views, including the third-party count that excludes the viewer;
* the Axelrod agents (Tit For Tat sequence, deceptive and honest talk, reproducible randomness by seed);
* LLM client: retries, JSON extraction, tolerant schemas, trace records, abort after consecutive failures;
* the society: full round-robin schedule, message timing per communication mode (including simultaneous writing
  inside an exchange), noise, the board, the reputation information reaching the decision, seed reproducibility;
* a crash mid-run followed by a resume gives results identical to an uninterrupted run;
* metrics (deception is detected exactly for the scripted liar), reports, the four-condition and multi-seed CLI.

**One tiny real-model run** (local `qwen2.5:3b`, 3 agents, 1 episode, 2 rounds, talk + ledger + board): 20 LLM calls,
0 failures, all artifacts produced. The 3B model played Alpha against a deceptive Defector and lost 0-10;
the run shows that the pipeline works with a real model, **not** anything about LLM behaviour (6 rounds is far too
little data).

**Not done, on purpose (per the instruction not to run long experiments):** no multi-seed runs, no capable-model runs,
no comparison between conditions with real models. The mock model ignores messages when it decides, so the
`talk` row of an offline `--conditions all` is only a plumbing check; do not read it as a finding.

**Known limitations to keep in mind when you interpret results:**

* The population is small and the opponent mix (honest reciprocator, deceptive defector) is a design choice.
* Simultaneous messages mean agents cannot negotiate within one exchange; use `exchanges >= 2` for dialogue.
* Reputation is a function of cooperation rate; richer standing rules (Nowak-Sigmund image scoring, norms that
  excuse punishing a known defector) are not implemented yet.
* LLM agents are not humans: they are trained on human text and tend to be agreeable. Results describe LLM agents.
* Axelrod handles pairwise matches only, so the multi-agent layer is custom code (`world.py`).

---

## Suggested next experiments

1. `--conditions all --seeds 1,2,3,4,5` with a capable model (start with `--episodes 2 --rounds 4`), to see whether
   talk and reputation raise cooperation and the LLM agents' points relative to classical ones.
2. Replace the deceptive Defector with a deceptive Tit For Tat or a conditional cooperator to test whether agents learn
   whom to believe.
3. Add `exchanges = 2` to allow negotiation, and mixed-model societies via per-agent `model`.
4. Add noise (`world.noise = 0.05`) to see whether forgiveness emerges.
5. Test whether agents punish third-party betrayers: compare `opening_by_third_party` between `watch` and `baseline`.
