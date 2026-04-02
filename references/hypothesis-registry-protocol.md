# Hypothesis Registry Protocol

Persist exploratory ideas as structured cards so later exploitation, reflection, or mixed strategies can reuse them.

## Card Fields

- `hypothesis_id`
- `title`
- `statement`
- `source_ids`
- `strategy_family`
- `expected_effect`
- `verify_plan`
- `guard_plan`
- `cost`
- `risk`
- `status`

## Status Lifecycle

- `proposed`: draft idea not yet reviewed
- `queued`: eligible for exploitation
- `ranked`: explicitly prioritized
- `selected`: currently active
- `tested`: experiment completed
- `retired`: no longer worth retrying

## Runtime Rules

- Keep the queue diverse across strategy families when possible.
- Do not test a hypothesis without first recording it in the registry.
- When a hypothesis is selected, set it as the active hypothesis in state.
- When a hypothesis is tested, link the experiment report back to the hypothesis id in iteration metadata and reporting.
