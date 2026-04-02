#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from autoresearch_helpers import (
    AutoresearchError,
    clone_research_state,
    empty_hypothesis_registry,
    hypothesis_record,
    load_json_or_default,
    read_state_payload,
    write_json,
    write_json_atomic,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persist ranked hypotheses gathered during exploration."
    )
    parser.add_argument("--state-path", default="autoresearch-state.json")
    parser.add_argument("--hypothesis-id", action="append", default=[])
    parser.add_argument("--title", action="append", default=[])
    parser.add_argument("--statement", action="append", default=[])
    parser.add_argument("--source-ids", action="append", default=[])
    parser.add_argument("--strategy-family", action="append", default=[])
    parser.add_argument("--expected-effect", action="append", default=[])
    parser.add_argument("--verify-plan", action="append", default=[])
    parser.add_argument("--guard-plan", action="append", default=[])
    parser.add_argument("--cost", action="append", default=[])
    parser.add_argument("--risk", action="append", default=[])
    parser.add_argument("--status", action="append", default=[])
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    required_groups = [
        args.hypothesis_id,
        args.title,
        args.statement,
        args.source_ids,
        args.strategy_family,
        args.expected_effect,
        args.verify_plan,
        args.guard_plan,
        args.cost,
        args.risk,
    ]
    if not args.hypothesis_id:
        raise AutoresearchError("At least one --hypothesis-id is required.")
    if len({len(group) for group in required_groups}) != 1:
        raise AutoresearchError("Hypothesis fields must have equal counts.")

    state_path = Path(args.state_path)
    payload = read_state_payload(state_path)
    research = clone_research_state(payload.get("state"), config=payload.get("config", {}))
    registry_path = Path(research["knowledge"]["hypothesis_registry_path"])
    registry = load_json_or_default(registry_path, empty_hypothesis_registry())
    if not isinstance(registry, dict) or not isinstance(registry.get("items"), list):
        raise AutoresearchError(f"Invalid hypothesis registry: {registry_path}")

    records = []
    for index, hypothesis_id in enumerate(args.hypothesis_id):
        records.append(
            hypothesis_record(
                hypothesis_id=hypothesis_id,
                title=args.title[index],
                statement=args.statement[index],
                source_ids=[item.strip() for item in args.source_ids[index].split(",") if item.strip()],
                strategy_family=args.strategy_family[index],
                expected_effect=args.expected_effect[index],
                verify_plan=args.verify_plan[index],
                guard_plan=args.guard_plan[index],
                cost=args.cost[index],
                risk=args.risk[index],
                status=args.status[index] if index < len(args.status) and args.status[index].strip() else "queued",
            )
        )

    existing_items = registry["items"]
    existing_ids = {item.get("hypothesis_id") for item in existing_items if isinstance(item, dict)}
    for record in records:
        if record["hypothesis_id"] in existing_ids:
            raise AutoresearchError(f"Duplicate hypothesis_id: {record['hypothesis_id']}")
        existing_items.append(record)

    write_json(registry_path, registry)
    research["phase"] = "exploration"
    research["exploration"]["status"] = "active"
    research["exploration"]["hypotheses_proposed"] = len(existing_items)
    research["exploration"]["hypotheses_ranked"] = len(
        [item for item in existing_items if isinstance(item, dict) and item.get("status") in {"queued", "ranked", "selected"}]
    )
    research["queued_hypothesis_ids"] = [
        item["hypothesis_id"]
        for item in existing_items
        if isinstance(item, dict) and item.get("status") in {"queued", "ranked", "selected"}
    ]
    if research["queued_hypothesis_ids"] and not research["active_hypothesis_id"]:
        research["active_hypothesis_id"] = research["queued_hypothesis_ids"][0]

    payload["state"]["phase"] = research["phase"]
    payload["state"]["knowledge"] = research["knowledge"]
    payload["state"]["exploration"] = research["exploration"]
    payload["state"]["queued_hypothesis_ids"] = research["queued_hypothesis_ids"]
    payload["state"]["active_hypothesis_id"] = research["active_hypothesis_id"]
    write_json_atomic(state_path, payload)

    print(
        json.dumps(
            {
                "state_path": str(state_path),
                "hypothesis_registry_path": str(registry_path),
                "hypothesis_ids": [record["hypothesis_id"] for record in records],
                "queued_hypothesis_ids": research["queued_hypothesis_ids"],
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
