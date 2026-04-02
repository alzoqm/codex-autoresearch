# Orchestration Protocol

Balance exploration and exploitation without abandoning the mechanical keep/discard loop.

## Purpose

Use this protocol when the run should mix:

- **explore**: novel strategy families, paper/doc/web-derived hypotheses, structural changes
- **exploit**: local refinement around the best retained strategy so far

## Controls

- `strategy_policy`: `fixed`, `epsilon_greedy`, or `ucb`
- `exploration_ratio`: target share of exploratory attempts, from `0` to `1`
- `exploration_sources`: allowed external evidence classes: `local`, `web`, `docs`, `papers`

## Runtime Rules

1. Before ideation, consult `autoresearch_orchestration_decide.py` when the next mode is unclear.
2. Keep every iteration mechanically verifiable regardless of mode.
3. Record orchestration metadata on every real experiment:
   - `--selection-mode explore|exploit`
   - `--strategy-family <family>`
   - `--evidence-source <source>` when non-local evidence informed the hypothesis
4. Exploration is allowed to try new strategy families; exploitation should stay close to a prior keep unless the scheduler says otherwise.
5. Search, docs, and papers are hypothesis inputs only. Final retention still depends on verify/guard outcomes.

## Policy Semantics

### `fixed`

Maintain the configured exploration share as a deterministic budget.

### `epsilon_greedy`

Honor the exploration budget first, then prefer the mode with the better average reward.

### `ucb`

Use reward plus uncertainty so under-sampled modes receive temporary priority.

## Logging

- Encode orchestration data as structured labels in the TSV:
  - `mode/explore` or `mode/exploit`
  - `family/<strategy-family>`
  - `source/<source>`
- Persist the aggregated orchestration summary in `autoresearch-state.json`.

## Stop Conditions

This protocol does not replace keep/discard, refine/pivot, or stop-condition logic. It only decides how the next hypothesis should be sourced.
