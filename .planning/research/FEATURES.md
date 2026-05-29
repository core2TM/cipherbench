# Feature Landscape: CipherBench (LLM Benchmark)

**Domain:** LLM evaluation benchmark — stateful cipher puzzles for AGI proximity measurement
**Researched:** 2026-05-28
**Confidence note:** Web search and WebFetch were unavailable in this environment. All findings are from training knowledge of ARC-AGI (2019–2024), BIG-Bench (2022), MMLU (2020), HumanEval (2021), HellaSwag (2019), Wordle/Mastermind-style evaluation literature, and NLP benchmark reproducibility research. Confidence levels reflect depth of primary-source documentation in training data.

---

## Table Stakes

Features every credible LLM benchmark must include. Missing any of these and the results cannot be cited, reproduced, or compared.

| Feature | Why Expected | Complexity | Confidence | Notes |
|---------|--------------|------------|------------|-------|
| **Seeded reproducibility** | Any run on the same seed must produce bit-identical results. Reviewers must be able to replicate a reported number. | Low | HIGH | ARC-AGI, HumanEval, and BIG-Bench all mandate this. Randomness without seeding is unpublishable. |
| **Canonical run configuration** | A single config file or CLI invocation that captures: model, provider, temperature, seed, attempt limit, puzzle difficulty parameters. Must be serialized alongside results. | Low | HIGH | Without captured config, scores are irreproducible even with the same seed. |
| **Per-session result record** | Every evaluation run produces a persisted record: puzzle ID/seed, all probe attempts with feedback received, final answer, success/fail, score. | Low | HIGH | Standard in HumanEval (JSONL), BIG-Bench (JSON per task), ARC-AGI (JSON output). Minimum granularity for debugging. |
| **Aggregate metrics** | Success rate (% correct final answers) and mean efficiency score across N runs, reported with N clearly stated. | Low | HIGH | Single-run numbers are noise. BIG-Bench requires ≥5 few-shot examples; HumanEval uses pass@k with multiple samples. |
| **Human baseline** | Human performance on the same tasks under the same conditions, used as the reference ceiling. | Medium | HIGH | ARC-AGI's human baseline (85%+) is what makes its numbers meaningful. Without it, "70% accuracy" has no interpretable referent for AGI proximity claims. |
| **Consistent task format** | Every puzzle instance presented to every model and human via identical prompt structure and feedback format. | Low | HIGH | Any format variation confounds results. The same CLI path must be used for humans and models. |
| **Provenance metadata** | Each result file records: benchmark version, date, model name/version, provider, all hyperparameters. | Low | HIGH | Required for longitudinal comparison as models improve. |
| **Failure mode visibility** | Results must show not just final score but how models failed — did they exhaust attempts, answer incorrectly on final try, fail to update hypotheses? | Medium | HIGH | This is what makes a benchmark scientifically useful vs just a leaderboard. |
| **Score definition documentation** | Precise mathematical definition of every metric. Ambiguous metrics cannot be compared across implementations. | Low | HIGH | MMLU and HumanEval both publish exact metric formulas. |
| **Session trace / replay** | Ability to inspect the full sequence of a session: prompt sent, feedback received, next probe, final answer. | Medium | HIGH | Without this, debugging model failures is impossible. ARC-AGI releases full task traces. |

---

## Differentiators

Features that make CipherBench novel, publishable, and not a commodity benchmark. These are the reasons the benchmark would be cited rather than ignored.

| Feature | Value Proposition | Complexity | Confidence | Notes |
|---------|-------------------|------------|------------|-------|
| **Stateful rule engine (history-dependent rules)** | Forces models to track state across turns. Existing cipher benchmarks treat each character independently. This breaks stationarity and eliminates pure n-gram pattern matching. | High | HIGH | No existing public benchmark combines statefulness + cipher + hidden feedback. ARC-AGI uses visual grid state but not sequential hidden-feedback loops. |
| **Cross-character interdependence** | Position-symmetric attacks fail because character transformations depend on neighboring characters. This breaks the most common LLM cipher-solving heuristic (positional lookup tables). | High | HIGH | Standard Caesar/Vigenere ciphers are trivially solved by current LLMs via memorized decoding tables. Cross-char mixing invalidates that approach. |
| **Hidden feedback (score-only, no ground truth reveal)** | Model receives only a similarity/correctness score per probe, not which characters were right. Forces genuine credit assignment under partial information — the Wordle/Mastermind mechanic applied to hypothesis-driven reasoning evaluation. | Medium | HIGH | This is a distinguishing mechanic. Most benchmarks reveal ground truth after each attempt (or give no feedback at all). Score-only feedback without ground truth reveal has been studied in Mastermind complexity theory but rarely in LLM evaluation. |
| **Procedural puzzle generation (unlimited fresh instances)** | Prevents dataset contamination and memorization. Models cannot improve by seeing training data that overlaps with the test set. Every evaluation uses fresh seeds. | Medium | HIGH | ARC-AGI uses a fixed test set (400 tasks) which is now partially contaminated. BIG-Bench is fixed. Procedural generation is the correct architectural response to the contamination problem. |
| **AGI proximity framing (human-normalized score)** | Final score expressed as a fraction of human baseline, not raw accuracy. "Model achieves 34% of human performance" is a concrete AGI distance signal. | Low | MEDIUM | This framing is what makes the benchmark scientifically meaningful beyond "accuracy on task X." Requires accurate, carefully-controlled human baseline collection. |
| **Composable difficulty axes** | State complexity, cross-char depth, and feedback granularity are independently tunable. This lets researchers study which dimension is the bottleneck for any given model. | Medium | MEDIUM | BIG-Bench does not decompose difficulty. ARC-AGI difficulty is implicit. Explicit axes make CipherBench a research instrument, not just a pass/fail test. |
| **Attempt efficiency as a first-class metric** | Not just did the model succeed, but how many probes did it need. A model that solves in 2 attempts vs 5 reveals different reasoning quality. | Low | HIGH | HumanEval uses pass@k implicitly but does not report probe efficiency as a reasoning-quality signal. This framing is novel. |
| **Same-interface human and model sessions** | Human plays through the exact same CLI path as model harness, ensuring no format advantage for either. | Low | HIGH | ARC-AGI's human baseline was collected via a dedicated web interface separate from the model API — introducing possible format differences. CipherBench's shared-path design is methodologically cleaner. |

---

## Anti-Features

Things to deliberately not build in v1. Each has a reason that is not just scope — it is a trap that would make the benchmark worse or compromise its validity.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Web UI / leaderboard in v1** | Premature public exposure locks in schema choices before the benchmark design is validated. Leaderboards invite gaming. A leaderboard without a canonical fixed puzzle set is meaningless (procedural seeds change per run). | CLI + local JSON results. Publish methodology first; leaderboard after canonical set is defined. |
| **Fixed canonical puzzle set in v1** | A fixed set becomes contaminated the moment it is public. The entire value of procedural generation is that the test set cannot be memorized. Locking a canonical set before the generator is validated inverts the design priority. | Validate the generator first; define a canonical set in a future milestone when the generator is stable and the contamination model is understood. |
| **Elo / head-to-head ranking in v1** | Elo requires many pairwise comparisons across a stable, fixed puzzle set. Procedural generation makes Elo unstable across runs (puzzles differ). Elo also obscures the absolute question: how close to human? | Compare all models against the human baseline. Human-normalized score is more interpretable for the AGI proximity claim than relative model rankings. |
| **Revealing ground truth after each attempt** | Giving the model the correct answer after a failed probe eliminates the credit assignment challenge. The entire scientific value of hidden feedback is that the model must reason from score alone. Any "hint" mode collapses the benchmark to a conventional Q&A task. | Strict score-only feedback throughout all 5 attempts. Ground truth revealed only in the session trace (post-session, for human inspection, not fed back to the model). |
| **Configurable attempt limit per run** | The 5-attempt limit is a core mechanic, not a parameter. Making it configurable in v1 means results across runs are incomparable. Efficiency scores have no meaning if attempt ceilings differ. | Fix at 5 in v1. Add configurability only after establishing what the baseline 5-attempt distribution looks like. |
| **Training data generation mode** | Benchmarks that double as training data generators have a fundamental conflict of interest: any model trained on generated data will look better on the benchmark. This destroys the benchmark's validity as an external evaluator. | Evaluation only. No export-to-finetune pipeline. |
| **Multi-modal tasks in v1** | Text-only ciphers are already novel and hard. Adding images or structured data expands the scope without clarifying the core hypothesis (does stateful hidden-feedback probe test structured reasoning?). | Establish the text cipher baseline first. Multi-modal is a future dimension if the core mechanic proves effective. |
| **Automatic prompt engineering / chain-of-thought scaffolding** | If the harness injects CoT prompts or auto-optimizes the prompt, it is benchmarking the prompt engineer, not the model. The model's reasoning must be its own. | Send a clean, unambiguous task description. Document the exact prompt used. Do not inject CoT scaffolding. |
| **Partial credit on final answer** | If a model gets 3/5 characters right on its final answer, reporting that as 0.6 success blurs the distinction between "solved" and "failed." The benchmark measures reasoning to a correct conclusion, not approximate correctness. | Binary success/fail on final answer. Efficiency score (attempts used) is the continuous signal. |
| **External database dependency** | Requiring PostgreSQL, Redis, or any server infrastructure blocks researchers from running the benchmark locally and increases setup friction to near-zero adoption. | Local JSON/CSV. Flat files are grep-able, git-committable, and need no infrastructure. |

---

## Feature Dependencies

```
Seeded reproducibility
  └── Canonical run configuration (seed is part of config)
       └── Per-session result record (config stored in record)
            └── Aggregate metrics (computed from records)
                 └── AGI proximity score (human-normalized aggregate)

Human baseline
  └── Same-interface human sessions (must use identical CLI path)
       └── AGI proximity framing (baseline is the denominator)

Procedural generator
  └── Stateful rule engine (generator calls rule engine)
       └── Cross-character interdependence (layer on top of base cipher)
            └── Hidden feedback mechanic (wraps rule engine output)
                 └── Attempt efficiency metric (counts probes against 5-limit)

Session trace / replay
  └── Per-session result record (trace is stored in the record)
       └── Failure mode visibility (trace makes failure inspectable)
```

---

## Prior Art: What Existing Benchmarks Do

### ARC-AGI (Chollet, 2019)
- **Table stakes it sets:** Fixed 400-task test set, human baseline ~85%, pixel-grid visual tasks, no language statistics to exploit, exact-match scoring only.
- **Limitation CipherBench addresses:** Fixed task set is now partially contaminated; tasks are stateless (each grid is independent); no sequential probe mechanic; human baseline collected via separate web UI (possible format confound).
- **Score reported:** % tasks solved exactly. No efficiency dimension.
- Confidence: HIGH — well-documented in Chollet's original paper and ARC Prize materials.

### BIG-Bench (Srivastava et al., 2022)
- **Table stakes it sets:** 204 tasks, standardized JSON task format, human rater baselines on a subset, few-shot evaluation protocol, normalized preferred metric per task.
- **Limitation CipherBench addresses:** Tasks are stateless Q&A; no sequential feedback loop; no procedural generation (fixed task JSON files); human baseline is crowd-sourced raters, not controlled sessions.
- **Score reported:** normalized preferred metric (accuracy, BLEU, etc.) per task; aggregate BIG-Bench score across tasks.
- Confidence: HIGH — open GitHub repo with full documentation in training data.

### MMLU (Hendrycks et al., 2020)
- **Table stakes it sets:** 57 subject areas, 4-choice multiple choice, exact-match scoring, no feedback between questions, chain-of-thought evaluation supported.
- **Limitation CipherBench addresses:** Entirely static; 5-choice surface pattern exploitable; no sequential reasoning required; well-known contamination in GPT-4 training data.
- **Score reported:** % correct per subject, macro-averaged overall accuracy.
- Confidence: HIGH.

### HumanEval (Chen et al., 2021)
- **Table stakes it sets:** 164 hand-written Python coding problems, pass@k metric (k=1,10,100), execution-based evaluation (not string match), model generates code that is run against unit tests.
- **Limitation CipherBench addresses:** Tasks are stateless; model sees full problem once; no iterative probe mechanic; contamination concerns for models trained post-2021.
- **Score reported:** pass@1, pass@10, pass@100 (unbiased estimator).
- Confidence: HIGH.

### HellaSwag (Zellers et al., 2019)
- **Table stakes it sets:** Adversarially filtered sentence completion, 4-choice, accuracy metric, human baseline ~95%.
- **Limitation CipherBench addresses:** Single-turn, no feedback, contamination rampant in modern LLMs (scores >95% on task that was designed to be hard for models).
- **Score reported:** % correct.
- Confidence: HIGH.

---

## Hidden Feedback / Wordle-Like Evaluation in Prior Work

**Summary:** This is sparse territory. Wordle-style feedback (color-coded partial match) has appeared in informal LLM probing studies but not as a published benchmark with human baselines and reproducibility infrastructure.

| Prior Work | Mechanic | Limitation vs CipherBench |
|------------|----------|--------------------------|
| Mastermind / Bulls-and-Cows complexity theory | Score-only feedback (bulls = exact, cows = present-wrong-position) | Algorithmic analysis, not LLM benchmark; no human baseline; no published evaluation harness. |
| Wordle LLM studies (blog posts, 2022–2023) | Give LLM Wordle feedback, measure solve rate | Informal; fixed 5-letter word vocabulary exploitable by frequency tables; not published benchmark; no reproducibility infrastructure; no human-controlled comparison. |
| BIG-Bench "few-shot interactive" tasks | Some tasks provide in-context feedback examples | Feedback is in-context demonstration, not real-time scored probe; model sees examples up front, not iterative probing. |
| ARC-AGI visual analogy | Provides input-output grid pairs as "training examples" | Not sequential probing; model sees all examples simultaneously; no score-only feedback; no attempt limit mechanic. |

**Conclusion:** There is no published LLM benchmark that combines (a) sequential probing with (b) score-only hidden feedback and (c) a reproducible harness with (d) a controlled human baseline. CipherBench occupies an empty niche. Confidence: MEDIUM (based on training knowledge through mid-2025; a thorough literature search might surface niche workshop papers).

---

## Human Baseline Capture: Standard Practice

| Benchmark | How Human Baseline Is Captured | Weakness |
|-----------|-------------------------------|----------|
| ARC-AGI | Dedicated web interface, recruited human solvers, 85.2% reported | Different interface than model API; possible UX advantage for humans |
| BIG-Bench | Mechanical Turk / recruited raters on a task subset | Crowd-source quality variance; not all 204 tasks have baselines |
| MMLU | Collected from domain experts and test prep; some tasks use prior exam statistics | Not a controlled live session; humans saw questions differently than models |
| HumanEval | Estimated from professional programmer performance; not formally measured | Self-reported / estimated, not rigorous controlled experiment |
| HellaSwag | Human accuracy on held-out adversarial set | Single-turn; no sequential feedback |

**CipherBench's approach is methodologically stronger than all of the above:** same CLI, same puzzle seed, same feedback format, same attempt limit for humans and models. This shared-path design is a genuine methodological contribution worth documenting in any paper.

---

## Session Replay / Trace Inspection: What Is Standard

| Feature | Standard In | Notes |
|---------|------------|-------|
| Full prompt/response log per attempt | HumanEval (via inspect harness), BIG-Bench | Considered minimum for debugging |
| Feedback received at each step | Specific to interactive benchmarks (rare) | Most benchmarks are single-turn |
| Final answer with pass/fail | Universal | |
| Intermediate reasoning inspection | Most benchmarks via "chain-of-thought" output | Stored as text in result JSONL |
| Replay CLI command | Not standard — usually just log files | CipherBench's session inspector is above-average DX |
| Diff between consecutive probes | Not standard in any major benchmark | Would be a differentiating DX feature |

---

## MVP Feature Priority

Build in v1:

1. Seeded reproducibility + canonical run config serialization
2. Per-session JSONL result record (all attempts, feedback, final answer, pass/fail, efficiency)
3. Binary success/fail + efficiency score aggregated over N runs
4. Human baseline via identical CLI path (same prompt format, same attempt limit)
5. Hidden feedback (score-only, no ground truth reveal mid-session)
6. Session trace inspector CLI command
7. Provenance metadata in every result file
8. Aggregate report: success rate, mean efficiency, human-normalized AGI proximity score

Defer:

- Canonical fixed puzzle set (validate generator first)
- Web UI / leaderboard (future milestone)
- Elo / head-to-head ranking (no value until canonical set exists)
- Multi-modal tasks
- Automatic CoT scaffolding
- Partial credit scoring

---

## Sources

- Confidence: HIGH for ARC-AGI, BIG-Bench, MMLU, HumanEval, HellaSwag feature descriptions — all based on their published papers and open-source repositories which were well-documented in training data through mid-2025.
- Confidence: MEDIUM for "hidden feedback in prior work" section — sparse literature; web search unavailable to verify recency.
- Confidence: HIGH for anti-features — derived from published post-mortems on benchmark gaming and contamination (e.g., Chollet's ARC Prize blog, BIG-Bench limitations discussion, MMLU contamination papers).
- Web search and WebFetch were both unavailable in this environment; no live URL verification was possible.
