# Retrospective: CipherBench

## Milestone: v1.0 — MVP

**Shipped:** 2026-05-30
**Phases:** 5 | **Plans:** 17 | **Tests:** 149 passing

### What Was Built

1. Three-layer cipher rule engine with enforced information boundary (`score_attempt()` only) and isolated RNG
2. Procedural puzzle generator with SHA-256 hash verification and EASY/MEDIUM/HARD difficulty tiers
3. Provider-agnostic model runner (LiteLLM) with atomic checkpointing, rate-limit resume, and HumanSessionRunner
4. Full scoring pipeline: success rate, efficiency score, AGI proximity vs. human baseline, per-difficulty breakdowns
5. Session inspector CLI (`cipherbench inspect`) replaying stored traces with Rich display

### What Worked

- **Inside-out build order**: Rule engine → puzzle generator → sessions → scoring → inspector. Each phase had a clear contract the next phase depended on; no backtracking needed.
- **Test-first on core mechanics**: Hypothesis property tests caught edge cases in the layer functions that hand-written tests missed. The 47-test phase gate at Phase 01 meant every subsequent phase built on a verified foundation.
- **Code review passes**: Two full review passes (pre- and post-Option-B fix) caught 14 total findings. Running the reviewer after design changes (not just after initial build) surfaced the most important fixes.
- **Symmetric encoding (Option B)**: The decision to use symmetric state+cross-char encoding for both guess and GT solved the trivial-AAAAA bug cleanly and made the correctness invariant obvious: submitting GT always scores is_correct=True on any round.

### What Was Inefficient

- **CR-01 was a design error that survived Phase 01 review**: The cross-char layer was a no-op when `ground_truth = alphabet[0] * n` — this should have been caught at Phase 02 when cross_char_depth was introduced. The fix required two passes: first applying CR-01 asymmetrically (which still left AAAAA trivially correct), then Option B properly fixing it.
- **Test probe hardcoding**: `test_different_seeds_produce_different_scores` used empirically-determined probes that needed updating twice (once per CR-01 fix pass). A property-based approach would have been more robust.

### Patterns Established

- **Symmetric encoding invariant**: When both sides of a comparison go through identical transformations, the correct answer is always the plaintext — no round-specific answer needed.
- **Two-pass review**: Run a code review after major design changes, not just after initial build. The post-Option-B review caught WR-01..WR-04 that didn't exist before the symmetric encoding change.
- **`rng.choice()` not `alphabet[0] * n`**: Any constant used as a "reference" or "ground truth" should be drawn from the seeded RNG so it participates in the reproducibility guarantee.

### Key Lessons

- The information boundary (RULE-04) is the load-bearing constraint — establish it in Phase 01 and never relax it. Every design decision thereafter flows from it.
- `inspect_session` raising `SystemExit(1)` is a service-level mistake deferred to v2. Service modules should raise domain exceptions; CLI wiring converts them to exit codes.
- Keep `output_length` threaded through extraction and prompt functions — hardcoding `5` anywhere creates a silent gap when someone uses a custom `DifficultyConfig`.

---

## Cross-Milestone Trends

| Metric | v1.0 |
|--------|------|
| Phases | 5 |
| Plans | 17 |
| Tests at close | 149 |
| Review findings | 14 (all resolved) |
| Timeline | 3 days (2026-05-28 → 2026-05-30) |
