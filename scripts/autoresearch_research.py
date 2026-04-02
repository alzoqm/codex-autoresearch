#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from autoresearch_core import (
    CORPUS_FILE_NAME,
    EXPERIMENT_REPORTS_DIRNAME,
    HYPOTHESIS_REGISTRY_NAME,
    RESEARCH_MODE_CHOICES,
    RESEARCH_PHASE_CHOICES,
    SOURCES_SUMMARY_NAME,
    AutoresearchError,
    utc_now,
)


def default_sources_summary_path(base_dir: Path) -> Path:
    return base_dir / SOURCES_SUMMARY_NAME


def default_corpus_path(base_dir: Path) -> Path:
    return base_dir / CORPUS_FILE_NAME


def default_hypothesis_registry_path(base_dir: Path) -> Path:
    return base_dir / HYPOTHESIS_REGISTRY_NAME


def default_experiment_reports_dir(base_dir: Path) -> Path:
    return base_dir / EXPERIMENT_REPORTS_DIRNAME


def normalize_research_mode(value: Any) -> str:
    if value in (None, ""):
        return "classic"
    normalized = str(value).strip().lower()
    if normalized not in RESEARCH_MODE_CHOICES:
        raise AutoresearchError(
            f"Unsupported research mode: {value!r}. "
            f"Expected one of: {', '.join(RESEARCH_MODE_CHOICES)}"
        )
    return normalized


def normalize_research_phase(value: Any, *, research_mode: str | None = None) -> str:
    if value in (None, ""):
        if normalize_research_mode(research_mode) == "research_first":
            return "exploration"
        return "exploitation"
    normalized = str(value).strip().lower()
    if normalized not in RESEARCH_PHASE_CHOICES:
        raise AutoresearchError(
            f"Unsupported research phase: {value!r}. "
            f"Expected one of: {', '.join(RESEARCH_PHASE_CHOICES)}"
        )
    return normalized


def _coerce_non_negative_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def normalize_positive_int(value: Any, *, field_name: str, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise AutoresearchError(f"Invalid {field_name}: {value!r}") from exc
    if parsed <= 0:
        raise AutoresearchError(f"{field_name} must be positive.")
    return parsed


def normalize_research_config(
    config: dict[str, Any] | None,
    *,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    base_dir = base_dir or Path.cwd()
    raw = dict(config or {})
    research_mode = normalize_research_mode(raw.get("research_mode"))
    exploration_phase_budget = normalize_positive_int(
        raw.get("exploration_phase_budget"),
        field_name="exploration phase budget",
        default=3 if research_mode == "research_first" else 1,
    )
    min_sources = normalize_positive_int(
        raw.get("min_sources"),
        field_name="min sources",
        default=8 if research_mode == "research_first" else 3,
    )
    min_hypotheses = normalize_positive_int(
        raw.get("min_hypotheses"),
        field_name="min hypotheses",
        default=3,
    )

    research = {
        "research_mode": research_mode,
        "exploration_phase_budget": exploration_phase_budget,
        "min_sources": min_sources,
        "min_hypotheses": min_hypotheses,
        "sources_summary_path": str(
            Path(raw.get("sources_summary_path") or default_sources_summary_path(base_dir))
        ),
        "corpus_path": str(Path(raw.get("corpus_path") or default_corpus_path(base_dir))),
        "hypothesis_registry_path": str(
            Path(raw.get("hypothesis_registry_path") or default_hypothesis_registry_path(base_dir))
        ),
        "experiment_reports_dir": str(
            Path(raw.get("experiment_reports_dir") or default_experiment_reports_dir(base_dir))
        ),
    }
    return research


def empty_research_state(
    config: dict[str, Any] | None,
    *,
    phase: str | None = None,
) -> dict[str, Any]:
    research = normalize_research_config(config or {})
    current_phase = normalize_research_phase(phase, research_mode=research["research_mode"])
    return {
        "phase": current_phase,
        "knowledge": {
            "sources_summary_path": research["sources_summary_path"],
            "corpus_path": research["corpus_path"],
            "hypothesis_registry_path": research["hypothesis_registry_path"],
            "experiment_reports_dir": research["experiment_reports_dir"],
        },
        "exploration": {
            "status": "active" if current_phase == "exploration" else "queued",
            "iterations_completed": 0,
            "budget_iterations": research["exploration_phase_budget"],
            "min_sources": research["min_sources"],
            "min_hypotheses": research["min_hypotheses"],
            "sources_collected": 0,
            "sources_shortlisted": 0,
            "hypotheses_proposed": 0,
            "hypotheses_ranked": 0,
            "last_query_set": [],
        },
        "active_hypothesis_id": "",
        "queued_hypothesis_ids": [],
        "last_report_path": "",
        "reflection_summary": [],
    }


def clone_research_state(
    state: dict[str, Any] | None,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    defaults = empty_research_state(config or {})
    if not isinstance(state, dict):
        return defaults
    cloned = deepcopy(defaults)
    phase = state.get("phase")
    if isinstance(phase, str):
        cloned["phase"] = normalize_research_phase(
            phase,
            research_mode=(config or {}).get("research_mode"),
        )
    knowledge = state.get("knowledge")
    if isinstance(knowledge, dict):
        for key in cloned["knowledge"]:
            value = knowledge.get(key)
            if isinstance(value, str) and value.strip():
                cloned["knowledge"][key] = value.strip()
    exploration = state.get("exploration")
    if isinstance(exploration, dict):
        status = exploration.get("status")
        if isinstance(status, str) and status.strip():
            cloned["exploration"]["status"] = status.strip()
        for key in (
            "iterations_completed",
            "budget_iterations",
            "min_sources",
            "min_hypotheses",
            "sources_collected",
            "sources_shortlisted",
            "hypotheses_proposed",
            "hypotheses_ranked",
        ):
            cloned["exploration"][key] = _coerce_non_negative_int(
                exploration.get(key),
                default=cloned["exploration"][key],
            )
        last_query_set = exploration.get("last_query_set")
        if isinstance(last_query_set, list):
            cloned["exploration"]["last_query_set"] = [
                str(item).strip() for item in last_query_set if str(item).strip()
            ]
    for key in ("active_hypothesis_id", "last_report_path"):
        value = state.get(key)
        if isinstance(value, str):
            cloned[key] = value.strip()
    queued = state.get("queued_hypothesis_ids")
    if isinstance(queued, list):
        cloned["queued_hypothesis_ids"] = [str(item).strip() for item in queued if str(item).strip()]
    reflection = state.get("reflection_summary")
    if isinstance(reflection, list):
        cloned["reflection_summary"] = [str(item).strip() for item in reflection if str(item).strip()]
    return cloned


def apply_research_state_updates(
    state: dict[str, Any] | None,
    *,
    config: dict[str, Any] | None = None,
    phase: str | None = None,
    active_hypothesis_id: str | None = None,
    queued_hypothesis_ids: list[str] | None = None,
    last_report_path: str | None = None,
    reflection_summary: list[str] | None = None,
    exploration_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    updated = clone_research_state(state, config=config)
    if phase is not None:
        updated["phase"] = normalize_research_phase(
            phase,
            research_mode=(config or {}).get("research_mode"),
        )
        updated["exploration"]["status"] = (
            "active" if updated["phase"] == "exploration" else "completed"
        )
    if active_hypothesis_id is not None:
        updated["active_hypothesis_id"] = active_hypothesis_id.strip()
    if queued_hypothesis_ids is not None:
        updated["queued_hypothesis_ids"] = [
            item.strip() for item in queued_hypothesis_ids if item and item.strip()
        ]
    if last_report_path is not None:
        updated["last_report_path"] = last_report_path.strip()
    if reflection_summary is not None:
        updated["reflection_summary"] = [
            item.strip() for item in reflection_summary if item and item.strip()
        ]
    if isinstance(exploration_updates, dict):
        for key, value in exploration_updates.items():
            if key == "last_query_set" and isinstance(value, list):
                updated["exploration"][key] = [
                    str(item).strip() for item in value if str(item).strip()
                ]
                continue
            if key == "status" and isinstance(value, str) and value.strip():
                updated["exploration"][key] = value.strip()
                continue
            if key in updated["exploration"]:
                updated["exploration"][key] = _coerce_non_negative_int(
                    value,
                    default=updated["exploration"][key],
                )
    return updated


def normalize_identifier(value: str, *, prefix: str) -> str:
    text = value.strip().lower()
    if not text:
        raise AutoresearchError(f"Missing {prefix} identifier.")
    normalized = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if not normalized:
        raise AutoresearchError(f"Invalid {prefix} identifier: {value!r}")
    return f"{prefix}-{normalized}" if not normalized.startswith(f"{prefix}-") else normalized


def load_json_or_default(path: Path, default: Any) -> Any:
    if not path.exists():
        return deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AutoresearchError(f"Invalid JSON file: {path}") from exc


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def render_sources_summary(records: list[dict[str, Any]]) -> str:
    lines = [
        "# Research Sources",
        "",
        "Condensed evidence gathered during exploration. Each entry links the original source and records the key takeaways reused by later hypotheses.",
        "",
    ]
    for record in records:
        lines.extend(
            [
                f"## {record['source_id']}: {record['title']}",
                f"- Type: {record['source_type']}",
                f"- URL: {record['url']}",
                f"- Retrieved: {record['retrieved_at']}",
                f"- Relevance: {record.get('relevance_score', 'n/a')}",
            ]
        )
        tags = record.get("tags") or []
        if tags:
            lines.append(f"- Tags: {', '.join(tags)}")
        lines.append("- Summary:")
        for bullet in record.get("summary_bullets") or []:
            lines.append(f"  - {bullet}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def source_record(
    *,
    source_id: str,
    title: str,
    url: str,
    source_type: str,
    summary_bullets: list[str],
    relevance_score: str = "",
    tags: list[str] | None = None,
    query: str = "",
) -> dict[str, Any]:
    return {
        "source_id": normalize_identifier(source_id, prefix="s"),
        "title": title.strip(),
        "url": url.strip(),
        "source_type": source_type.strip().lower(),
        "summary_bullets": [bullet.strip() for bullet in summary_bullets if bullet.strip()],
        "relevance_score": relevance_score.strip(),
        "tags": [tag.strip().lower() for tag in (tags or []) if tag.strip()],
        "query": query.strip(),
        "retrieved_at": utc_now(),
        "used_by_hypotheses": [],
    }


def empty_hypothesis_registry() -> dict[str, Any]:
    return {"version": 1, "items": []}


def hypothesis_record(
    *,
    hypothesis_id: str,
    title: str,
    statement: str,
    source_ids: list[str],
    strategy_family: str,
    expected_effect: str,
    verify_plan: str,
    guard_plan: str,
    cost: str,
    risk: str,
    status: str = "queued",
) -> dict[str, Any]:
    return {
        "hypothesis_id": normalize_identifier(hypothesis_id, prefix="h"),
        "title": title.strip(),
        "statement": statement.strip(),
        "source_ids": [normalize_identifier(item, prefix="s") for item in source_ids],
        "strategy_family": strategy_family.strip(),
        "expected_effect": expected_effect.strip(),
        "verify_plan": verify_plan.strip(),
        "guard_plan": guard_plan.strip(),
        "cost": cost.strip(),
        "risk": risk.strip(),
        "status": status.strip(),
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }


def build_experiment_report_markdown(
    *,
    experiment_id: str,
    hypothesis_id: str,
    source_ids: list[str],
    iteration: str,
    outcome: str,
    metric_before: str,
    metric_after: str,
    summary: str,
    code_changes: list[str],
    reflection: list[str],
    next_steps: list[str],
) -> str:
    lines = [
        f"# {experiment_id}",
        "",
        "## Hypothesis",
        hypothesis_id,
        "",
        "## Evidence",
    ]
    for source_id in source_ids:
        lines.append(f"- {source_id}")
    lines.extend(
        [
            "",
            "## Outcome",
            f"- Iteration: {iteration}",
            f"- Status: {outcome}",
            f"- Metric before: {metric_before}",
            f"- Metric after: {metric_after}",
            f"- Summary: {summary}",
            "",
            "## Code Changes",
        ]
    )
    for item in code_changes:
        lines.append(f"- {item}")
    lines.extend(["", "## Reflection"])
    for item in reflection:
        lines.append(f"- {item}")
    lines.extend(["", "## Next Steps"])
    for item in next_steps:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)
