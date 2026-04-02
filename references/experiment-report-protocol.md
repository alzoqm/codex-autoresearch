# Experiment Report Protocol

Every tested hypothesis should produce a reusable report, even when the iteration is discarded.

## Required Sections

- Hypothesis
- Evidence
- Outcome
- Code Changes
- Reflection
- Next Steps

## Report Intent

- Preserve why a trial was attempted.
- Capture what changed and how the result was measured.
- Record reflection that can feed lessons, future exploration, or mixed strategies.

## Minimal Practice

- Write one report per tested hypothesis, not per source.
- Keep the reflection concrete: what generalized, what failed, what should be tried next.
- Pass the report path into `autoresearch_record_iteration.py --report-path ...` so the runtime state keeps a pointer to the latest report.
