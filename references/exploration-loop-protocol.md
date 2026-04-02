# Exploration Loop Protocol

Use this protocol when the run should begin with research rather than immediate code edits.

## Goal

Turn a user objective into a reusable evidence base, a ranked hypothesis queue, and a clean handoff into the standard exploitation loop.

## Required Outputs

- `research-sources.md`: human-readable source summary with links and key takeaways
- `research-corpus.jsonl`: machine-readable source records
- `hypothesis-registry.json`: ranked hypothesis cards backed by source ids
- `experiment-reports/EXP-*.md`: structured reports for each tested hypothesis

## Phase Order

1. Decompose the goal into 3-7 research questions.
2. Search papers, official docs, and the web according to the allowed exploration sources.
3. Curate sources with concise summaries and stable source ids.
4. Generate multiple hypotheses grounded in those source ids.
5. Rank hypotheses by expected impact, feasibility, and testability.
6. Enter exploitation only after the configured minimum source and hypothesis thresholds are met, unless a blocker is logged.

## Rules

- Search results are evidence inputs, not accepted solutions.
- Every curated source must include a URL and 1-5 concise summary bullets.
- Every hypothesis must cite at least one source id.
- Exploration should stay artifact-first: write the source and hypothesis files before major code edits.
- If exploration runs out of useful sources, log the blocker or fall back to `classic` mode explicitly.

## Helper Scripts

- `python3 <skill-root>/scripts/autoresearch_collect_sources.py ...`
- `python3 <skill-root>/scripts/autoresearch_generate_hypotheses.py ...`
- `python3 <skill-root>/scripts/autoresearch_write_experiment_report.py ...`
