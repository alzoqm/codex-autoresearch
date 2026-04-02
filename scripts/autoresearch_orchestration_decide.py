#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from autoresearch_helpers import (
    AutoresearchError,
    parse_results_log,
    read_state_payload,
    resolve_state_path_for_log,
)
from autoresearch_orchestration import decide_selection_mode, empty_orchestration_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select the next exploration/exploitation mode from autoresearch state."
    )
    parser.add_argument("--results-path", default="research-results.tsv")
    parser.add_argument("--state-path")
    parser.add_argument("--strategy-policy")
    parser.add_argument("--exploration-ratio")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    results_path = Path(args.results_path)
    repo_hint = results_path.parent if results_path.is_absolute() else None
    parsed = parse_results_log(results_path)
    state_path = resolve_state_path_for_log(args.state_path, parsed, cwd=repo_hint)
    payload = read_state_payload(state_path)
    config = payload.get("config", {})

    decision = decide_selection_mode(
        strategy_policy=args.strategy_policy or config.get("strategy_policy"),
        exploration_ratio=(
            args.exploration_ratio
            if args.exploration_ratio is not None
            else config.get("exploration_ratio")
        ),
        orchestration_summary=payload.get("state", {}).get(
            "orchestration",
            empty_orchestration_summary(),
        ),
    )
    decision["results_path"] = str(results_path)
    decision["state_path"] = str(state_path)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AutoresearchError as exc:
        raise SystemExit(f"error: {exc}")
