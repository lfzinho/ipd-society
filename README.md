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
through Ollama (local) or OpenRouter (paid API). One capable-model experiment has been run ([Results](#results-the-first-capable-model-experiment)); see
[Validation](#validation-and-what-it-does-not-show) for exactly what has and has not been tested. Step 1, the
single-agent baseline, is the sibling project `../bold-bardeen`.

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

## Results: the first capable-model experiment

*Written as a short article. Raw data: `examples/haiku_results/` (per-run `metrics.json` and `report.md`, plus
`comparison.md`). This is the first real result of Steps 2 and 3, and it is small. Read the
[threats to validity](#5-threats-to-validity) before quoting any number.*

### Abstract

We place three LLM agents (`anthropic/claude-haiku-5.5`) in a five-agent society with two scripted agents, an honest
Tit For Tat and a deceptive Defector, and let every pair play a short repeated Prisoner's Dilemma (neutral labels
Alpha/Beta). We vary two social channels, **messages** before each round and a **public ledger** of past moves, in a
2 x 2 design, with three seeds per cell. Messages roughly doubled cooperation (22% to 41%, with little run-to-run
spread). The ledger on its own *reduced* cooperation (22% to 9%). Both channels together gave an unstable society: one
seed cooperated at 42% and another collapsed to 5%. A partner's promise of Alpha was met with Alpha about half the
time; a promise of Beta was met with Alpha **never**. LLM agents out-earned the scripted agents in every condition.

### 1. Question and motivation

Step 1 (`../bold-bardeen`) measured one LLM against *fixed* opponents and found that a capable model plays near the
best achievable score when it is told who the opponent is, and loses 10 to 25 points of efficiency when it is not.
That setting has a known optimum and no social structure. The question here is the one in the project's title:
**how do LLM agents behave in repeated social dilemmas when they can communicate and see each other's reputation?**
Concretely:

1. Does cheap talk (non-binding messages) change cooperation, and do the agents lie?
2. Does a verifiable public record of past behaviour change who cooperates with whom?
3. Do the two interact?

Related work is in `../bold-bardeen/docs/research/literature-review.md`: Akata et al. 2023 and Fontana et al. 2024 for
LLMs in repeated games, Park et al. 2023 for the memory design, and Piatti et al. 2024 and Vallinder and Hughes 2024
for societies of LLM agents.

### 2. Method

**Game.** Per round, own points / partner points: both Alpha 3/3, I play Alpha and the partner Beta 0/5, the reverse
5/0, both Beta 1/1. Labels are neutral so that the words "Prisoner's Dilemma", "cooperate" and "defect" do not trigger
memorised behaviour.

**Society.** Five agents: **Ada, Bo, Cy** (LLM, each with a memory stream), **Dee** (scripted, honest Tit For Tat,
says what it will play) and **Eli** (scripted, always Beta but *promises* Alpha, a deliberate liar). Each episode is a
full round-robin (10 matches); a match is 4 rounds; there are 2 episodes. That is 20 matches and 80 rounds per run.
Agents know the match length. After each match every LLM agent writes an observation and a reflection into its memory.

**Conditions** (the same agents, prompts and seed under each; see [the four conditions](#the-four-standard-conditions)):
`baseline` (no messages, no record), `talk` (one message swap before every round), `watch` (the ledger: each agent
sees every agent's cooperation rate and betrayal count, and the partner's recent rounds), `talk_watch` (both, plus the
public board).

**Model and replication.** `anthropic/claude-haiku-5.5` via OpenRouter, temperature 0.4, seeds 1, 2 and 3, 12 runs in
total, 0 failed LLM calls and so 0 fallback moves. The seed changes the match schedule and the scripted randomness;
it does not make the model deterministic. Command:

```powershell
python main.py --provider openrouter --model anthropic/claude-haiku-5.5 --conditions all --seeds 1,2,3 --episodes 2 --rounds 4 --output-dir output_haiku
```

**Measures** (definitions in [Metrics](#metrics-what-they-mean-and-why)): cooperation rate (share of Alpha),
mutual-Alpha rate, points per round for LLM and scripted agents, promises and broken promises, cooperation after a
promise, and the opening move of each match (first round only) split by the partner's public record.

### 3. Results

Mean ± standard deviation over 3 seeds (20 matches, 80 rounds per seed):

| Condition | Cooperation | Mutual Alpha | Points/round, LLM | Points/round, scripted | Promises broken |
|---|---|---|---|---|---|
| baseline | 22% ± 14 | 14% ± 13 | 1.68 ± 0.32 | 1.26 ± 0.25 | n/a |
| talk | **41% ± 3** | 32% ± 3 | **2.12 ± 0.11** | 1.59 ± 0.09 | 36% ± 4 |
| watch | 9% ± 4 | 2% ± 3 | 1.34 ± 0.09 | 1.08 ± 0.08 | n/a |
| talk_watch | 24% ± 19 | 17% ± 18 | 1.77 ± 0.48 | 1.20 ± 0.29 | 37% ± 5 |

Per-seed cooperation, to show the spread behind the means:

| Condition | Seed 1 | Seed 2 | Seed 3 |
|---|---|---|---|
| baseline | 12% | 26% | 33% |
| talk | 38% | 41% | 44% |
| watch | 6% | 13% | 7% |
| talk_watch | 23% | 42% | **5%** |

**Finding 1: messages raise cooperation, reliably.** Every `talk` seed (38-44%) is above every `baseline` seed
(12-33%), and the `talk` spread is small. In `talk` the LLM agents average 2.12 points per round against 1.68 in
`baseline`; the mutual-Alpha rate more than doubles (14% to 32%).

**Finding 2: a promise carries information, and a Beta promise is a perfect signal.** The share of the LLM agents'
moves that were Alpha, by what their partner had just promised (`talk` condition):

| Partner promised | seed 1 | seed 2 | seed 3 |
|---|---|---|---|
| Alpha | 48% (n=75) | 59% (n=78) | 55% (n=85) |
| Beta | 0% (n=14) | 0% (n=14) | 0% (n=6) |
| nothing | 14% (n=7) | 0% (n=4) | 0% (n=5) |

An announced Beta was never met with Alpha. A promised Alpha was trusted about half the time, in a society where 36%
of promises are broken (all of Eli's are). The model sees the message text, so this shows that agents *use* what they
are told; it cannot show *why* (that needs reading `trace.jsonl`).

**Finding 3: the ledger alone lowered cooperation.** In `watch`, cooperation is 9% and mutual Alpha is 2%, against
22% and 14% in `baseline`. Partners with a bad public record (below 50% cooperation) received an Alpha opening in 0 of
54 cases across the three seeds. But only 5 openings in total involved a partner with a *good* record, so this cannot
separate "the agent reacts to reputation" from "everyone has a bad record because everyone defects". A plausible
mechanism is a spiral: the first betrayal is visible to everyone, every agent then defects against the betrayer, and
those defections are in turn recorded. We have **not** verified this in the traces; it is a hypothesis.

**Finding 4: with both channels, the outcome depends on the seed.** `talk_watch` cooperated at 23%, 42% and 5%. In
seed 3 the society collapsed: partners promised Alpha 43 times and the agents answered none of those promises with
Alpha, so the messages stopped being believed. Seed 2, with the same configuration, reached 42%, higher than any
`baseline` or `watch` run; there, openings against partners with a good record (n=12) got Alpha 100% of the time
against 29% (n=7) for bad records. So when the dynamic starts well, talk plus a record can support cooperation, and
when it starts badly nothing recovers it. Three seeds cannot say how often each happens.

**Finding 5: the LLM agents out-earn the scripted agents in every condition** (2.12 vs 1.59 in `talk`). In `talk`
the always-Beta Eli earns about 1.5 points per round while the LLM agents earn 1.8-2.4, so Eli's lie pays less than it
would against fixed opponents. The honest Tit For Tat, Dee, does worst in `watch` (0.75-0.94 points per round).

**Finding 6: end-game defection is strong.** Cooperation in the last round of a match is 0-15% in every run, against
7-54% in earlier rounds. With a known, short horizon this is expected, and it means part of the lost cooperation is a
design effect (see below). Cooperation also falls from episode 1 to episode 2 in most runs.

### 4. Discussion

The strongest result is the simplest: **letting these agents talk makes them cooperate more**, and a stated intention
to defect is always believed. The most interesting is the least certain: **showing them a verifiable record made them
*less* cooperative**, and combining it with talk made the society fragile. One consistent story is that a record lets
agents *punish* faster than it lets them *trust*, since one visible betrayal is a reason to defect and nothing in the
record offers a way back. That is a hypothesis about the mechanism. If it holds, it is a warning for systems that give
agents a reputation score without a way to repair it.

It also adds to Step 1. There, a model that was told who it faced played near the optimum. Here, with no information
(`baseline`), a capable model cooperated only 22% of the time in a society that contains a defector. The high
efficiency in Step 1 came from knowing what to expect; without that the model is cautious.

### 5. Threats to validity

* **Three seeds, 20 matches per run.** The `baseline` (±14) and `talk_watch` (±19) spreads are large, so only the
  `talk` and `watch` effects are clearly outside the noise. No significance test was run.
* **Short, known horizon (4 rounds).** End-game defection (Finding 6) probably lowers cooperation everywhere. A longer
  or unknown horizon is the first thing to change.
* **One model, one society.** The three LLM agents are the same model with the same prompt apart from a persona line,
  and there is one scripted liar and one honest reciprocator. Results describe haiku-5.5 in this population.
* **The mechanisms behind Findings 3 and 4 are unverified.** The traces exist (`trace.jsonl`, not kept in the
  repository because of size) but have not been read systematically.
* **The reputation comparison is confounded** when nearly all partners have a bad record (Finding 3). The
  `opening_by_third_party` rows also show a gap with reputation *off*, which is a correlation, not a response; do not
  read them as an effect.
* **The `promise` tag is self-reported by the model.**
* LLM output is not deterministic even at a fixed seed.

### 6. What this adds, and what comes next

Together with Step 1 there is now a chain of evidence: a capable model plays near-optimally when informed (Step 1),
cooperates only moderately when uninformed, is moved upward by cheap talk, and is moved downward, or made unstable,
by a public record (this experiment). Next, in order of value: (1) read the `watch` and `talk_watch` seed-3 traces to
confirm or reject the spiral hypothesis; (2) a longer or geometric horizon; (3) 5-10 seeds so that Finding 4 can be
quantified; (4) a ledger that forgives (decays old betrayals) to test the "no way back" hypothesis; (5) mixed-model
societies. The single-agent baseline and the literature review are in `../bold-bardeen`.

### 7. Reproduction and cost

The run took 3,986 LLM calls (240 per run without messages, 432 with messages, plus a few resumed matches). My
pre-run estimate of about 2,000 calls was low by roughly a factor of two because it missed some calls. By the
OpenRouter balance the run cost roughly $1.3, about $0.0003 per call. To reproduce, use the command in Section 2, and
try `--episodes 1 --rounds 2` first.

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

**Capable-model experiment:** see [Results](#results-the-first-capable-model-experiment) (haiku-5.5, 4 conditions,
3 seeds, 3,986 calls, 0 failures). The mock model ignores messages when it decides, so the `talk` row of an offline
`--conditions all` is only a plumbing check; do not read it as a finding.

**Known limitations to keep in mind when you interpret results:**

* The population is small and the opponent mix (honest reciprocator, deceptive defector) is a design choice.
* Simultaneous messages mean agents cannot negotiate within one exchange; use `exchanges >= 2` for dialogue.
* Reputation is a function of cooperation rate; richer standing rules (Nowak-Sigmund image scoring, norms that
  excuse punishing a known defector) are not implemented yet.
* LLM agents are not humans: they are trained on human text and tend to be agreeable. Results describe LLM agents.
* Axelrod handles pairwise matches only, so the multi-agent layer is custom code (`world.py`).

---

## Suggested next experiments

1. Read the traces of the collapsed runs, then extend the experiment to 5-10 seeds and a longer horizon (see Results, section 6).
2. Replace the deceptive Defector with a deceptive Tit For Tat or a conditional cooperator to test whether agents learn
   whom to believe.
3. Add `exchanges = 2` to allow negotiation, and mixed-model societies via per-agent `model`.
4. Add noise (`world.noise = 0.05`) to see whether forgiveness emerges.
5. Test whether agents punish third-party betrayers: compare `opening_by_third_party` between `watch` and `baseline`.
