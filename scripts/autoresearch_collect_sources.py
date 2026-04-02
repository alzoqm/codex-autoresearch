#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from autoresearch_helpers import (
    AutoresearchError,
    append_jsonl,
    clone_research_state,
    normalize_identifier,
    parse_results_log,
    read_state_payload,
    render_sources_summary,
    resolve_state_path_for_log,
    results_repo_root,
    source_record,
    write_json_atomic,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Append curated exploration sources and persist them into research artifacts."
    )
    parser.add_argument("--results-path", default="research-results.tsv")
    parser.add_argument("--state-path")
    parser.add_argument("--source-id", action="append", default=[])
    parser.add_argument("--title", action="append", default=[])
    parser.add_argument("--url", action="append", default=[])
    parser.add_argument("--source-type", action="append", default=[])
    parser.add_argument("--summary", action="append", default=[])
    parser.add_argument("--relevance-score", action="append", default=[])
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    return parser


def _value_at(values: list[str], index: int, *, default: str = "") -> str:
    if index < len(values):
        return values[index]
    return default


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.source_id:
        raise AutoresearchError("At least one --source-id is required.")
    if not (
        len(args.source_id)
        == len(args.title)
        == len(args.url)
        == len(args.source_type)
        == len(args.summary)
    ):
        raise AutoresearchError(
            "--source-id, --title, --url, --source-type, and --summary must have equal counts."
        )

    results_path = Path(args.results_path)
    parsed = parse_results_log(results_path)
    state_path = resolve_state_path_for_log(args.state_path, parsed, cwd=results_path.parent)
    payload = read_state_payload(state_path)
    research = clone_research_state(payload.get("state"), config=payload.get("config", {}))

    sources_summary_path = Path(research["knowledge"]["sources_summary_path"])
    corpus_path = Path(research["knowledge"]["corpus_path"])

    new_records = []
    tag_values = [tag.strip() for tag in args.tag if tag.strip()]
    for index, source_id in enumerate(args.source_id):
        record = source_record(
            source_id=source_id,
            title=args.title[index],
            url=args.url[index],
            source_type=args.source_type[index],
            summary_bullets=[piece.strip() for piece in args.summary[index].split("||") if piece.strip()],
            relevance_score=_value_at(args.relevance_score, index),
            tags=tag_values,
            query=_value_at(args.query, index),
        )
        new_records.append(record)

    append_jsonl(corpus_path, new_records)

    all_records = []
    if corpus_path.exists():
        for line in corpus_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                all_records.append(json.loads(line))
    sources_summary_path.parent.mkdir(parents=True, exist_ok=True)
    sources_summary_path.write_text(render_sources_summary(all_records), encoding="utf-8")

    exploration = research["exploration"]
    exploration["sources_collected"] = len(all_records)
    exploration["sources_shortlisted"] = len(all_records)
    query_set = exploration.get("last_query_set", [])
    query_set.extend(query.strip() for query in args.query if query.strip())
    seen = set()
    exploration["last_query_set"] = [
        item for item in query_set if not (item in seen or seen.add(item))
    ]
    research["phase"] = "exploration"
    research["exploration"]["status"] = "active"

    payload["state"]["phase"] = research["phase"]
    payload["state"]["knowledge"] = research["knowledge"]
    payload["state"]["exploration"] = exploration
    write_json_atomic(state_path, payload)

    print(
        json.dumps(
            {
                "results_path": str(results_path),
                "state_path": str(state_path),
                "sources_summary_path": str(sources_summary_path),
                "corpus_path": str(corpus_path),
                "source_ids": [record["source_id"] for record in new_records],
                "sources_collected": exploration["sources_collected"],
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
