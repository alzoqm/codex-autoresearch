#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from autoresearch_helpers import (
    AutoresearchError,
    build_experiment_report_markdown,
    clone_research_state,
    normalize_identifier,
    read_state_payload,
    write_json_atomic,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a structured experiment report tied to a hypothesis."
    )
    parser.add_argument("--state-path", default="autoresearch-state.json")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--hypothesis-id", required=True)
    parser.add_argument("--iteration", required=True)
    parser.add_argument("--outcome", required=True)
    parser.add_argument("--metric-before", required=True)
    parser.add_argument("--metric-after", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--source-id", action="append", default=[])
    parser.add_argument("--code-change", action="append", default=[])
    parser.add_argument("--reflection", action="append", default=[])
    parser.add_argument("--next-step", action="append", default=[])
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    state_path = Path(args.state_path)
    payload = read_state_payload(state_path)
    research = clone_research_state(payload.get("state"), config=payload.get("config", {}))

    experiment_id = normalize_identifier(args.experiment_id, prefix="exp").upper()
    hypothesis_id = normalize_identifier(args.hypothesis_id, prefix="h")
    source_ids = [normalize_identifier(item, prefix="s") for item in args.source_id]
    reports_dir = Path(research["knowledge"]["experiment_reports_dir"])
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{experiment_id}.md"
    report_path.write_text(
        build_experiment_report_markdown(
            experiment_id=experiment_id,
            hypothesis_id=hypothesis_id,
            source_ids=source_ids,
            iteration=args.iteration,
            outcome=args.outcome,
            metric_before=args.metric_before,
            metric_after=args.metric_after,
            summary=args.summary,
            code_changes=args.code_change,
            reflection=args.reflection,
            next_steps=args.next_step,
        ),
        encoding="utf-8",
    )

    research["last_report_path"] = str(report_path)
    research["active_hypothesis_id"] = hypothesis_id
    if args.reflection:
        research["reflection_summary"] = [item.strip() for item in args.reflection if item.strip()]
    if args.outcome.strip().lower() in {"keep", "discard", "crash"}:
        research["phase"] = "exploitation"
        research["exploration"]["status"] = "completed"

    payload["state"]["phase"] = research["phase"]
    payload["state"]["last_report_path"] = research["last_report_path"]
    payload["state"]["active_hypothesis_id"] = research["active_hypothesis_id"]
    payload["state"]["reflection_summary"] = research["reflection_summary"]
    payload["state"]["exploration"] = research["exploration"]
    write_json_atomic(state_path, payload)

    print(
        json.dumps(
            {
                "state_path": str(state_path),
                "report_path": str(report_path),
                "experiment_id": experiment_id,
                "hypothesis_id": hypothesis_id,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AutoresearchError as exc:
        raise SystemExit(f"error: {exc}")
