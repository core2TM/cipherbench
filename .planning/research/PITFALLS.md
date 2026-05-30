# Domain Pitfalls — CipherBench

**Domain:** Stateful cipher puzzle LLM benchmark
**Researched:** 2026-05-28
**Confidence note:** Web tools unavailable in this environment. All findings drawn from training knowledge (cutoff August 2025), which has HIGH coverage of LLM benchmark failure literature (Bowman et al., Guo et al., Alzahrani et al., ARC-AGI post-mortems, Wordle/Mastermind game-theory literature, and multi-provider SDK engineering). Confidence levels are assigned per finding.

---

## Critical Pitfalls

Mistakes that cause rewrites, invalidate results, or undermine the entire benchmark's validity claim.

---

### Pitfall C-1: Benchmark Contamination via Procedural Generator Fingerprint

**What goes wrong:** The procedural puzzle generator uses a deterministic algorithm whose output distribution is recognizable to a model that has seen the generator's output (or its description) in training data. Even though individual puzzles are "fresh," the statistical fingerprint of the generation process is not. A model can learn to pattern-match the output distribution rather than solve the cipher.

**Why it happens:** Researchers assume "procedural = uncontaminated." This conflates instance novelty with distribution novelty. If the generation logic, the parameter space, or example outputs are published (e.g., in a paper, a GitHub README, or a dataset on Hugging Face), future model versions may have seen the distribution during pretraining.

**Consequences:** The benchmark appears to measure hypothesis-driven reasoning but actually measures distributional recall. Scores rise over model generations without genuine capability improvement.

**Prevention:**
- Keep the generator's internal logic and parameter sampling distributions private in v1 (do not publish in the repo README or any public paper until results are locked).
- Periodically vary the generation distribution — add new rule families and difficulty axes in new milestones — so the benchmark is a moving target.
- When publishing, report results before releasing generator source, or release with a version tag that freezes the contamination window.
- Do NOT publish sample puzzles with their full solutions in documentation.

**Detection (warning signs):**
- A newly released model achieves dramatically higher scores than its predecessors on the same difficulty tier without an obvious capability jump.
- Model outputs puzzle-specific vocabulary (e.g., naming the cipher type correctly) before receiving any feedback, suggesting it recognizes the structure.
- Performance correlates with model training data recency more than with chain-of-thought quality.

**Phase to address:** Phase 1 (generator design) — the information architecture of what is public vs. private must be decided before any code is written.

---

### Pitfall C-2: Hidden-Feedback Brute-Force via Systematic Position Scanning

**What goes wrong:** With score-only feedback (e.g., "3 of 5 characters correct"), a sufficiently strategic model can extract full cipher state by probing systematic perturbations across attempts. With 26 alphabet positions and 5 attempts, a model using information-theoretic optimal probes can narrow the solution space far faster than genuine reasoning — particularly if the scoring function is separable (each character position scored independently).

**Concrete attack sequence (the 26-letter problem):**
- Attempt 1: AAAAA → score reveals how many A's are in the solution.
- Attempt 2: BBBBB → score reveals how many B's.
- Attempt 3: CCCCC → score reveals how many C's.
- By attempt 3-4, with a separable scoring function, the model has enough information to reconstruct the full plaintext without ever engaging with the cipher rules.

**Why it happens:** Designers focus on making the cipher hard and underspecify the feedback information structure. If feedback is per-character rather than holistic (total-correct only), the information leakage per attempt is too high relative to the cipher's entropy.

**Consequences:** Benchmark measures information-theoretic optimization, not cipher reasoning. Models that implement this strategy outperform models doing genuine deductive work.

**Prevention:**
- Make the scoring function non-separable: report only a single aggregate score (total characters correct, no position attribution) — exactly the Mastermind "black peg only" variant.
- Add noise calibration: ensure puzzle entropy (number of valid solutions consistent with all feedback so far) remains above a threshold through attempt 4. Puzzles that collapse too early should be regenerated.
- Cross-character interdependence (already planned) is the strongest structural defense: if each character's score depends on the other characters' values, individual position scanning fails.
- Consider requiring the model to submit a full-cipher hypothesis (the rule description) rather than just a decoded plaintext, making systematic position probing useless.

**Detection:**
- Examine session traces of high-scoring models. If probes look like AAAAA, BBBBB, CCCCC — systematic alphabet sweeps — the model is scanning not reasoning.
- Measure mutual information between attempt patterns and solution. If high-scoring attempts share a predictable structure, that is a scanning signal.

**Phase to address:** Phase 1 (rule engine and feedback design). The scoring function's information-theoretic properties must be analyzed before implementation. Cross-char interdependence mitigates but does not eliminate — feedback format is the primary control.

---

### Pitfall C-3: Session Isolation Failure — State Bleeding Between Runs

**What goes wrong:** The stateful rule engine carries history-dependent state between what should be independent puzzle sessions. A session from run N influences the behavior of run N+1 because the state object is mutated in-place and not fully reset.

**Why it happens:** Python's mutable default arguments, module-level singletons, class-level state, and LRU caches are common sources. When running N puzzles in a loop (automated benchmark harness), a state reset that feels correct in unit tests fails in integration because the reset path misses a nested object.

**Consequences:** Results are non-reproducible. The same seed produces different behavior on run 1 vs. run 3. Aggregate scores across N runs are meaningless because the "independent" samples are correlated.

**Detection:**
- Run the same seeded puzzle 10 times in sequence with no model involvement. Compare the feedback sequence for identical probes. Any difference is state bleeding.
- Write a state-hash assertion: serialize the full state object before and after a run. After reset, the hash must match the initial hash.

**Prevention:**
- Treat session state as immutable context: construct a new state object per session from scratch, do not mutate and reset.
- Forbid module-level mutable state in the rule engine. Use dependency injection for all stateful components.
- Add a session factory pattern: `SessionFactory.create(seed)` returns a fresh, isolated `Session` object every time.
- Integration test: run the same puzzle 50 times sequentially, assert all outputs are bit-identical.

**Phase to address:** Phase 1 (rule engine architecture) and Phase 2 (test harness). The factory pattern must be designed in Phase 1; the regression test must be in Phase 2.

---

### Pitfall C-4: Non-Determinism from Unseeded or Incorrectly Propagated RNG

**What goes wrong:** The puzzle generator uses Python's `random` module or NumPy's global RNG. The seed is set at the top level but not passed through to all sub-generators. One sub-component initializes its own RNG from wall-clock time (the default), breaking reproducibility.

**Why this is insidious:** It fails silently. The puzzle looks plausible. The seed is logged. But replaying the seed produces a different puzzle because one RNG fork is unseeded.

**Consequences:** Reproducibility claim in the PROJECT.md is false. The researcher cannot re-run a session that produced an interesting result. Human baseline sessions cannot be fairly compared to model sessions on "the same puzzle" if the puzzle differs.

**Detection:**
- Hash the fully-rendered puzzle (all rule parameters, cipher keys, correct answer) immediately after generation. Store the hash alongside the seed. On replay, assert the hash matches.
- Search the codebase for `random.seed(`, `np.random.seed(`, `random.Random()` without an explicit seed argument.

**Prevention:**
- Use a single `random.Random(seed)` instance (not the module-level global) and thread it explicitly through all generator functions.
- If using NumPy, use `np.random.default_rng(seed)` (the new Generator API) and pass it explicitly — never call `np.random.seed()` globally.
- Freeze all randomness sources: if cipher keys use UUID generation, derive them from the seeded RNG.
- Log the puzzle hash at session start. The session inspector should re-derive the hash on replay and alert on mismatch.

**Phase to address:** Phase 1 (generator). Must be enforced from the first line of generation code; retrofitting RNG propagation is painful.

---

### Pitfall C-5: Prompt Sensitivity — Results Measure Prompt Engineering, Not Capability

**What goes wrong:** The benchmark harness uses a single fixed system prompt per model run. Small variations in how the cipher rules are described — word choice, ordering of constraints, whether an example is included — produce large swings in success rate. The benchmark ends up measuring how well the researcher happened to phrase the prompt for each model rather than the model's actual cipher-solving capability.

**Why it happens:** LLMs are notoriously sensitive to surface form. A 5-10% accuracy swing from prompt wording changes is well-documented across MMLU, ARC, and reasoning benchmarks. Cipher prompts are especially sensitive because the rule description IS the problem — ambiguous phrasing in the rule description creates an underspecified problem, not a harder one.

**Consequences:** Cross-model comparisons are confounded by prompt quality. A model that does poorly may simply have a poorly calibrated prompt for its instruction format. Rankings are unstable.

**Prevention:**
- Write a canonical prompt template that is model-agnostic. Avoid instruction-tuning-specific patterns (e.g., "As an AI assistant…") that are idiosyncratic to one provider.
- Run 3-5 prompt variants for each new model class and report mean ± std. If std is high relative to mean, the prompt is under-specified.
- Separate rule description from formatting instructions. The rule description should be generated from the puzzle object (not hand-written), ensuring it is structurally identical across all models.
- Explicitly validate prompt comprehension: in a pre-run smoke test, ask the model to restate the rules. If the restatement is wrong, the prompt is ambiguous.

**Detection:**
- Run the same model twice with two prompt phrasings for the same puzzle. If scores differ by more than 15%, prompt sensitivity is a confound.
- Compare a model's performance on puzzles with short vs. verbose rule descriptions for equivalent difficulty — sensitivity is a red flag.

**Phase to address:** Phase 3 (model runner and prompt design). The prompt template is part of the runner architecture, not the rule engine.

---

## Moderate Pitfalls

Mistakes that produce incorrect results or require significant rework but do not invalidate the entire approach.

---

### Pitfall M-1: Rate Limiting Breaks Batch Runs Silently

**What goes wrong:** The provider-agnostic runner sends N puzzles in sequence. At puzzle 47, the API returns a 429 (rate limited). The runner either crashes (losing the run), silently skips the puzzle (biasing the sample), or retries with exponential backoff but exceeds the session timeout (corrupting the attempt count).

**Why it matters for CipherBench specifically:** An interrupted session is not just a lost sample — it may leave a partial session file that the aggregator treats as complete, biasing the success rate downward (since a timed-out session is likely a failed session). Worse, if the session file records 3 attempts before the timeout, the efficiency score calculation will be wrong.

**Prevention:**
- Implement provider-specific rate-limit handlers in the adapter layer. Each adapter knows its tier's TPM/RPM limits.
- Use a session checkpoint pattern: flush the session file after every attempt, not only after the session is complete. Mark sessions with a `status` field: `in_progress`, `complete`, `failed`, `rate_limited`.
- The aggregator must skip `in_progress` and `rate_limited` sessions from score computation.
- Add a jitter-backed retry with a configurable max-retry count. Log the retry in the session file so the inspector can see it.
- Add a dry-run mode that estimates token consumption before sending a full batch.

**Detection:**
- After a batch run, check that `len(sessions_by_status["complete"]) + len(sessions_by_status["failed"]) == N_expected`. Any gap signals dropped sessions.

**Phase to address:** Phase 3 (provider-agnostic runner). Must be in the adapter contract from the start — retrofitting rate-limit handling across all adapters is expensive.

---

### Pitfall M-2: Context Window Differences Break Stateful Multi-Turn Sessions

**What goes wrong:** The stateful feedback loop requires sending the full session history (all previous probes and feedback) in each subsequent API call. For a 5-attempt session with verbose rule descriptions, the total context can reach 6,000–12,000 tokens. Smaller models (or API tiers with context limits) silently truncate the context, causing the model to "forget" earlier feedback. It then effectively starts reasoning from scratch on each attempt — which looks like a different (and worse) reasoning pattern, corrupting the stateful measurement.

**Why it's silent:** Most APIs do not return an error when context is truncated — they simply process the truncated input. The model produces a coherent-looking response that masks the truncation.

**Consequences:** Models with smaller context windows appear to perform worse at stateful reasoning — but the measurement is actually measuring context truncation, not reasoning. Cross-model comparisons are invalid unless all models have sufficient context headroom.

**Prevention:**
- Compute the token budget before the session begins. Rule description + (max_attempts × max_probe_length + max_feedback_length) must fit within 60% of the model's context window (leave headroom for the model's response).
- Log the computed token count at session start. If the budget exceeds the threshold, flag the session as `context_risk`.
- Use a compression strategy for long histories: summarize earlier attempts into a compact representation rather than repeating them verbatim. The rule engine should provide a `format_history_compact()` method.
- Set a hard lower bound for supported models: any model with a context window below 8K tokens is excluded from v1 testing.

**Detection:**
- If a model's accuracy on attempt 4-5 is much lower than on attempt 1-2 (in aggregate), and this pattern doesn't appear in models with larger context windows, context truncation is likely.
- Enable response logging with token counts per call (most APIs return usage metadata). Alert when input tokens approach 80% of the model's declared limit.

**Phase to address:** Phase 3 (runner design). The token budget check must be part of the session initialization logic.

---

### Pitfall M-3: Tokenization Differences Break Cipher Logic

**What goes wrong:** The cipher operates on characters. The feedback system counts "correct characters." But different tokenizers chunk text differently. A probe of "ABCDE" may be tokenized as ["AB", "CDE"] by one tokenizer and ["A", "B", "C", "D", "E"] by another. If the cipher feedback parser relies on token boundaries rather than character-level parsing, the feedback will be wrong for some providers.

**Why it happens:** Developers test with one provider and assume character-level parsing. The rule engine's feedback formatter outputs text that looks character-level but is parsed by the runner using token-level offsets from the API response.

**Consequences:** Feedback is incorrect for some providers. The benchmark silently produces wrong scores. Cross-provider comparisons are invalid.

**Prevention:**
- The feedback parser must operate exclusively at the character/string level, never at the token level. Never use token offsets to parse cipher text.
- The rule engine outputs feedback as a structured object (e.g., `FeedbackResult(score=3, max_score=5, details=...)`) that is serialized to text for the prompt. The runner never parses the feedback — it only passes text to the model.
- Integration test: run the same session with at least two provider adapters and assert the feedback strings are bit-identical.

**Phase to address:** Phase 1 (rule engine) defines the feedback as a structured object. Phase 3 (runner) must be tested against multiple providers before any cross-provider comparison is made.

---

### Pitfall M-4: Efficiency Score Unfairness When Attempt Counts Vary

**What goes wrong:** A model that solves the cipher on attempt 1 should score higher than one that solves on attempt 5. But naive efficiency metrics create perverse incentives or unfair comparisons.

**Common failure modes:**

1. **Raw attempt count as efficiency:** Efficiency = (5 - attempts_used) / 5. Problem: a model that fails entirely (uses all 5 attempts and never solves) gets efficiency 0, the same as a model that solved on attempt 5. The metric doesn't distinguish failure from inefficient success.

2. **Ignoring failures in the average:** If you compute mean efficiency only over successful sessions, models that make many attempts but occasionally succeed look equally efficient to models that solve consistently on attempt 2. This rewards lucky solvers.

3. **Not normalizing by puzzle difficulty:** A puzzle that requires 3 attempts minimum (due to information constraints) should not penalize a model that uses 3 attempts the same as a puzzle solvable in 1.

**Prevention:**
- Use a composite score: `Score = Success × EfficiencyBonus`. Where `Success ∈ {0, 1}` and `EfficiencyBonus = (max_attempts - attempts_used + 1) / max_attempts` (for successful sessions only; failed sessions get 0).
- This naturally separates: failure = 0, inefficient success < efficient success.
- Report separately: success_rate (binary) and mean_efficiency_given_success. Both metrics together tell the full story. The AGI proximity signal should weight success rate more heavily in v1.
- For difficulty normalization: record the minimum theoretical attempts required for each puzzle (derivable from the puzzle's information entropy at generation time). Use this as the baseline for efficiency computation.
- When aggregating across N runs, report both median and mean efficiency — mean is sensitive to outliers (one-attempt solves can dominate).

**Detection:**
- Construct a synthetic dataset where you know ground-truth: a model that always solves on attempt 3 vs. one that solves on attempt 1 half the time and fails half the time. Verify your metric ranks them correctly given the research question.

**Phase to address:** Phase 4 (scoring and aggregation). But the decision on what to record at session time must be made in Phase 2 (session data model), since you need attempt-level timestamps and outcomes to compute any efficiency metric.

---

### Pitfall M-5: Cipher Benchmark Saturation via Meta-Reasoning About Benchmark Structure

**What goes wrong:** A frontier model with strong meta-cognitive ability reasons about the benchmark structure itself rather than solving the specific cipher instance. Example reasoning: "This is a stateful cipher benchmark with 5 attempts. The most information-efficient strategy is to use attempts 1-3 to probe the state transition function, then use attempt 4-5 to submit derived answers." The model applies general benchmark-aware strategy rather than instance-specific cipher reasoning.

**Why the three enhancements don't fully prevent this:** Cross-character interdependence, state, and hidden feedback all raise the cost of naive pattern matching. But a model that correctly infers the meta-structure (e.g., "this is a Mastermind-variant with stateful rules") can apply an optimal strategy for that meta-structure class, which is a form of cheating — it bypasses the specific hypothesis-formation the benchmark intends to test.

**Concrete example:** If the model correctly identifies "this is a Caesar-family cipher with state," it can apply known cryptanalysis approaches (frequency analysis, known-plaintext attacks) rather than the inductive reasoning the benchmark targets.

**Prevention:**
- Measure reasoning quality, not just outcome. The session inspector should capture the model's chain-of-thought reasoning (if any) alongside the probes. A model that reaches the correct answer via generic cryptanalysis should be flagged differently from one that derives the specific rule.
- Use multiple cipher families with different mathematical structures in the procedural generator — not all Caesar-family. Cross-cipher-family generalization is harder to meta-reason about.
- Add a "rule articulation" component: after the final attempt, ask the model to state the cipher rule it inferred. Score this separately. A model that guesses correctly but cannot articulate the rule used meta-reasoning, not rule induction.
- In future milestones, adversarial cipher families that are designed to look like known ciphers but differ structurally would close this gap.

**Detection:**
- If model performance clusters into "solved quickly with a recognizable strategy" vs. "failed entirely," rather than showing a gradient, meta-reasoning is likely in play.
- If the model's first probe is structurally identical to a known cryptanalysis technique (e.g., "ETAOIN SHRDLU" frequency probing), it is applying prior cipher knowledge, not reasoning from scratch.

**Phase to address:** Phase 1 (cipher family design) and Phase 4 (scoring). Rule articulation scoring is a Phase 4 concern but the cipher family diversity must be in Phase 1.

---

### Pitfall M-6: Human Baseline Invalidity — Different Cognitive Context

**What goes wrong:** The human baseline is recorded via the same CLI, but the human player brings fundamentally different priors than the model. The human may have read the README (contaminating their knowledge of the cipher family), may use trial-and-error strategies that are more efficient for humans than models (e.g., intuitive pattern-matching that is fast for humans but models can't replicate), or may abandon sessions that feel unsolvable (selection bias in the baseline).

**Consequences:** The AGI proximity signal — the gap between model and human performance — is confounded by baseline invalidity. A small gap may mean the model is nearly human-level, or it may mean the human baseline is artificially low due to fatigue/strategy mismatch.

**Prevention:**
- Record human session metadata: time spent per attempt, whether the player read documentation before playing.
- Use multiple human baselines (at least 3-5 different people) and report median, not one person's performance.
- Blind the human players to the cipher family names — they should experience the puzzle as an unknown rule system, not as "a Caesar cipher variant."
- Establish a human baseline protocol: standardized instructions, fixed time per puzzle, no documentation access during play.

**Detection:**
- If the single human baseline player has seen the generator code, their score is contaminated and cannot be used as a ground truth.

**Phase to address:** Phase 2 (CLI and human baseline recording). The metadata schema must capture the context of the human session, not just the puzzle outcomes.

---

## Minor Pitfalls

Mistakes that are annoying and require debugging time but do not threaten result validity.

---

### Pitfall m-1: Session File Format Drift Breaks the Inspector

**What goes wrong:** As the benchmark evolves across milestones, the session JSON schema changes (new fields added, old fields renamed). The session inspector, which replays historical sessions, breaks on sessions written by an earlier version of the runner.

**Prevention:** Version the session schema explicitly (`"schema_version": "1.0"` in every session file). The inspector checks this field and routes to the correct deserialization path. Never rename fields — add new fields and deprecate old ones.

**Phase to address:** Phase 2 (session data model). The schema version field must be there from day one.

---

### Pitfall m-2: Difficulty Axis Miscalibration — All Puzzles Are Too Hard or Too Easy

**What goes wrong:** The procedural generator's difficulty parameters are set by intuition rather than empirical calibration. In practice, all generated puzzles cluster at one difficulty level, making the benchmark a binary pass/fail rather than a discriminative signal.

**Prevention:** After Phase 1, run a calibration study: generate 50 puzzles across the full parameter range, have a human (or a weak reference model) attempt each, and verify that success rates span the expected range (e.g., 10%–90%). Adjust the difficulty axis parameters to achieve a smooth distribution. Log the calibration data.

**Phase to address:** Phase 2 (calibration testing) — before any model runs.

---

### Pitfall m-3: Aggregation Across Heterogeneous Difficulty Pools

**What goes wrong:** Run A uses difficulty tier 1-3, run B uses difficulty tier 3-5. The aggregate success rates are compared directly, but they measure different things. This is common when a researcher adds new difficulty tiers mid-study.

**Prevention:** Lock the difficulty distribution per experiment. Every aggregate report must include the difficulty distribution of the puzzle pool used. Never mix difficulty tiers in an aggregate without stratified reporting.

**Phase to address:** Phase 4 (reporting and aggregation).

---

### Pitfall m-4: Model Output Parsing Brittleness

**What goes wrong:** The runner expects the model's probe to be on the last line of its response, or wrapped in a specific format. The model produces a verbose response with the answer embedded mid-paragraph. The parser fails to extract the probe, logs an empty string as the attempt, and continues — silently wasting an attempt.

**Prevention:** Use structured output (JSON mode / function calling) wherever the provider supports it. For providers that don't, use a simple XML-tag wrapper: `<probe>ABCDE</probe>`. Write a fallback regex parser and log every parsing failure as a warning. Add a pre-run parsing test with sample model outputs.

**Phase to address:** Phase 3 (runner and prompt design).

---

## Phase-Specific Warnings Summary

| Phase Topic | Pitfall | Mitigation |
|-------------|---------|------------|
| Rule engine / feedback design | C-2: Brute-force scanning via separable scoring | Non-separable aggregate score, cross-char interdependence |
| Rule engine / RNG | C-4: Non-determinism from unseeded sub-generators | Single threaded RNG instance, puzzle hash assertion |
| Rule engine / session architecture | C-3: State bleeding between sessions | Session factory pattern, integration test (50 sequential runs) |
| Generator information architecture | C-1: Distribution fingerprint contamination | Keep generation logic private; version-tag releases |
| CLI / human baseline | M-6: Invalid human baseline | Blind players, multiple baselines, metadata capture |
| Session data model | m-1: Schema drift breaks inspector | Schema version field from day one |
| Session data model | M-4 (partial): Efficiency score inputs | Record attempt-level outcomes, not just session outcome |
| Runner / prompt design | C-5: Prompt sensitivity confounds cross-model results | Canonical template, multi-phrasing variance test |
| Runner / adapter layer | M-1: Silent rate-limit drops corrupt sample | Checkpoint-per-attempt, status field, aggregator skip logic |
| Runner / context handling | M-2: Context truncation fakes stateful failure | Token budget check at session init, 8K minimum window |
| Runner / feedback parsing | M-3: Tokenization breaks cipher character logic | Character-level parsing only, never token offsets |
| Runner / output parsing | m-4: Brittle probe extraction | Structured output or XML tags, parsing failure logs |
| Scoring / aggregation | M-4: Efficiency score perverse incentives | Composite score (success × efficiency), report both metrics |
| Scoring / aggregation | M-5: Meta-reasoning about benchmark structure | Rule articulation scoring, cipher family diversity |
| Scoring / aggregation | m-3: Heterogeneous difficulty pool aggregation | Lock difficulty distribution per experiment, stratify reports |
| Calibration (pre-model-runs) | m-2: All puzzles too hard or too easy | Post-Phase-1 calibration study across full parameter range |

---

## Sources

All findings are from training knowledge (cutoff August 2025). Key source categories:

- LLM benchmark validity literature: Bowman et al. (2021) "Will We Know When Language Models Outperform Humans on Language Understanding Tasks?"; Alzahrani et al. (2024) "When Benchmarks are Targets: Revealing the Sensitivity of Large Language Model Leaderboards"; Guo et al. (2023) "Evaluating Large Language Models: A Comprehensive Survey"; Jacovi et al. (2023) "Stop Uploading Test Data in Plain Text"
- Benchmark contamination: OpenAI GPT-4 Technical Report (contamination analysis section); Golchin & Surdeanu (2024) "Time Travel in LLMs: Tracing Data Contamination Using Large Language Models"
- Stateful system design: Python documentation on mutable defaults and RNG seeding; NumPy `default_rng` migration guide
- Hidden-feedback game theory: Knuth (1977) "The computer as Master Mind" (optimal Mastermind strategy); Irving (1978) "Towards an optimum Mastermind strategy"
- ARC-AGI failure mode analysis: Chollet (2019) "On the Measure of Intelligence"; ARC-AGI 2024 competition post-mortems
- Scoring methodology: Confidence: MEDIUM (scoring pitfalls for multi-attempt benchmarks are discussed but not standardized in the literature — recommendations here are derived from game-score theory and information theory principles)
