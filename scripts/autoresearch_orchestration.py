#!/usr/bin/env python3
from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from autoresearch_core import AutoresearchError, normalize_labels, parse_decimal


SELECTION_MODE_CHOICES = ("explore", "exploit")
STRATEGY_POLICY_CHOICES = ("fixed", "epsilon_greedy", "ucb")
EXPLORATION_SOURCE_CHOICES = ("local", "web", "docs", "papers")
DEFAULT_STRATEGY_POLICY = "fixed"
DEFAULT_EXPLORATION_RATIO = Decimal("0")
MODE_LABEL_PREFIX = "mode/"
FAMILY_LABEL_PREFIX = "family/"
SOURCE_LABEL_PREFIX = "source/"


def _coerce_int(value: Any, *, default: int = 0) -> int:
    try:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.strip():
            return int(value.strip())
    except (TypeError, ValueError):
        return default
    return default


def normalize_strategy_family(value: str | None) -> str | None:
    if value is None:
        return None
    pieces = [piece.strip().lower() for piece in str(value).replace("_", "-").split()]
    family = "-".join(piece for piece in pieces if piece)
    if not family:
        return None
    labels = normalize_labels([family])
    return labels[0] if labels else None


def normalize_selection_mode(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized:
        return None
    if normalized not in SELECTION_MODE_CHOICES:
        raise AutoresearchError(
            f"Unsupported selection mode: {value!r}. "
            f"Expected one of: {', '.join(SELECTION_MODE_CHOICES)}"
        )
    return normalized


def normalize_strategy_policy(value: str | None) -> str:
    if value in (None, ""):
        return DEFAULT_STRATEGY_POLICY
    normalized = str(value).strip().lower()
    if normalized not in STRATEGY_POLICY_CHOICES:
        raise AutoresearchError(
            f"Unsupported strategy policy: {value!r}. "
            f"Expected one of: {', '.join(STRATEGY_POLICY_CHOICES)}"
        )
    return normalized


def normalize_exploration_ratio(value: Any) -> Decimal:
    if value in (None, ""):
        return DEFAULT_EXPLORATION_RATIO
    ratio = parse_decimal(value, "exploration ratio")
    if ratio < 0 or ratio > 1:
        raise AutoresearchError("Exploration ratio must be between 0 and 1 inclusive.")
    return ratio


def normalize_exploration_sources(values: Any) -> list[str]:
    if values in (None, "", []):
        return []
    if isinstance(values, str):
        raw_values = [values]
    else:
        try:
            raw_values = list(values)
        except TypeError as exc:
            raise AutoresearchError(f"Invalid exploration sources: {values!r}") from exc
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        for piece in str(raw).split(","):
            source = piece.strip().lower()
            if not source:
                continue
            if source not in EXPLORATION_SOURCE_CHOICES:
                raise AutoresearchError(
                    f"Unsupported exploration source: {source!r}. "
                    f"Expected one of: {', '.join(EXPLORATION_SOURCE_CHOICES)}"
                )
            if source not in seen:
                seen.add(source)
                normalized.append(source)
    return normalized


def orchestration_labels(
    *,
    selection_mode: str | None = None,
    strategy_family: str | None = None,
    evidence_sources: list[str] | None = None,
) -> list[str]:
    labels: list[str] = []
    normalized_mode = normalize_selection_mode(selection_mode)
    normalized_family = normalize_strategy_family(strategy_family)
    normalized_sources = normalize_exploration_sources(evidence_sources or [])
    if normalized_mode is not None:
        labels.append(f"{MODE_LABEL_PREFIX}{normalized_mode}")
    if normalized_family is not None:
        labels.append(f"{FAMILY_LABEL_PREFIX}{normalized_family}")
    labels.extend(f"{SOURCE_LABEL_PREFIX}{source}" for source in normalized_sources)
    return labels


def merge_orchestration_labels(
    base_labels: Any,
    *,
    selection_mode: str | None = None,
    strategy_family: str | None = None,
    evidence_sources: list[str] | None = None,
) -> list[str]:
    merged = normalize_labels(base_labels)
    auto_labels = orchestration_labels(
        selection_mode=selection_mode,
        strategy_family=strategy_family,
        evidence_sources=evidence_sources,
    )
    for label in auto_labels:
        if label not in merged:
            merged.append(label)
    return merged


def extract_orchestration_context(labels: Any) -> dict[str, Any]:
    normalized = normalize_labels(labels)
    selection_mode = None
    strategy_family = None
    evidence_sources: list[str] = []
    for label in normalized:
        if label.startswith(MODE_LABEL_PREFIX):
            candidate = label[len(MODE_LABEL_PREFIX) :]
            if candidate in SELECTION_MODE_CHOICES:
                selection_mode = candidate
        elif label.startswith(FAMILY_LABEL_PREFIX):
            strategy_family = normalize_strategy_family(label[len(FAMILY_LABEL_PREFIX) :])
        elif label.startswith(SOURCE_LABEL_PREFIX):
            source = label[len(SOURCE_LABEL_PREFIX) :]
            if source in EXPLORATION_SOURCE_CHOICES and source not in evidence_sources:
                evidence_sources.append(source)
    return {
        "selection_mode": selection_mode,
        "strategy_family": strategy_family,
        "evidence_sources": evidence_sources,
    }


def empty_orchestration_summary() -> dict[str, Any]:
    return {
        "attempts_by_mode": {mode: 0 for mode in SELECTION_MODE_CHOICES},
        "keeps_by_mode": {mode: 0 for mode in SELECTION_MODE_CHOICES},
        "non_keeps_by_mode": {mode: 0 for mode in SELECTION_MODE_CHOICES},
        "reward_by_mode": {mode: 0 for mode in SELECTION_MODE_CHOICES},
        "last_selection_mode": "",
        "last_strategy_family": "",
        "last_evidence_sources": [],
        "family_stats": {},
    }


def clone_orchestration_summary(summary: dict[str, Any] | None) -> dict[str, Any]:
    cloned = empty_orchestration_summary()
    if not isinstance(summary, dict):
        return cloned
    for key in ("attempts_by_mode", "keeps_by_mode", "non_keeps_by_mode", "reward_by_mode"):
        value = summary.get(key)
        if isinstance(value, dict):
            for mode in SELECTION_MODE_CHOICES:
                cloned[key][mode] = _coerce_int(value.get(mode, 0))
    last_selection_mode = summary.get("last_selection_mode")
    if isinstance(last_selection_mode, str):
        cloned["last_selection_mode"] = last_selection_mode
    last_strategy_family = summary.get("last_strategy_family")
    if isinstance(last_strategy_family, str):
        cloned["last_strategy_family"] = last_strategy_family
    cloned["last_evidence_sources"] = normalize_exploration_sources(
        summary.get("last_evidence_sources", [])
    )
    family_stats = summary.get("family_stats")
    if isinstance(family_stats, dict):
        normalized_families: dict[str, dict[str, Any]] = {}
        for raw_family, raw_stats in family_stats.items():
            family = normalize_strategy_family(str(raw_family))
            if family is None or not isinstance(raw_stats, dict):
                continue
            normalized_families[family] = {
                "attempts": _coerce_int(raw_stats.get("attempts", 0)),
                "keeps": _coerce_int(raw_stats.get("keeps", 0)),
                "non_keeps": _coerce_int(raw_stats.get("non_keeps", 0)),
                "last_status": str(raw_stats.get("last_status", "")),
                "selection_mode": str(raw_stats.get("selection_mode", "")),
                "evidence_sources": normalize_exploration_sources(
                    raw_stats.get("evidence_sources", [])
                ),
            }
        cloned["family_stats"] = normalized_families
    return cloned


def apply_iteration_to_orchestration(
    summary: dict[str, Any] | None,
    *,
    status: str,
    labels: Any,
) -> dict[str, Any]:
    updated = clone_orchestration_summary(summary)
    context = extract_orchestration_context(labels)
    selection_mode = context["selection_mode"]
    strategy_family = context["strategy_family"]
    evidence_sources = context["evidence_sources"]
    if selection_mode is None and strategy_family is None and not evidence_sources:
        return updated

    if selection_mode is not None:
        updated["last_selection_mode"] = selection_mode
    if strategy_family is not None:
        updated["last_strategy_family"] = strategy_family
    if evidence_sources:
        updated["last_evidence_sources"] = list(evidence_sources)

    if strategy_family is not None:
        family_stats = updated["family_stats"].setdefault(
            strategy_family,
            {
                "attempts": 0,
                "keeps": 0,
                "non_keeps": 0,
                "last_status": "",
                "selection_mode": selection_mode or "",
                "evidence_sources": list(evidence_sources),
            },
        )
        family_stats["last_status"] = status
        if selection_mode is not None:
            family_stats["selection_mode"] = selection_mode
        if evidence_sources:
            family_stats["evidence_sources"] = list(evidence_sources)
    else:
        family_stats = None

    if selection_mode is None:
        return updated

    updated["attempts_by_mode"][selection_mode] += 1
    if family_stats is not None:
        family_stats["attempts"] += 1

    if status == "keep":
        updated["keeps_by_mode"][selection_mode] += 1
        updated["reward_by_mode"][selection_mode] += 1
        if family_stats is not None:
            family_stats["keeps"] += 1
    elif status in {"discard", "crash", "no-op"}:
        updated["non_keeps_by_mode"][selection_mode] += 1
        updated["reward_by_mode"][selection_mode] -= 1
        if family_stats is not None:
            family_stats["non_keeps"] += 1
    return updated


def orchestration_summary_from_rows(rows: list[Any]) -> dict[str, Any]:
    summary = empty_orchestration_summary()
    for row in rows:
        if getattr(row, "main_iteration", None) is None or getattr(row, "status", "") == "baseline":
            continue
        summary = apply_iteration_to_orchestration(
            summary,
            status=str(getattr(row, "status", "")),
            labels=getattr(row, "labels", ()),
        )
    return summary


def _mode_attempts(summary: dict[str, Any], mode: str) -> int:
    attempts = summary.get("attempts_by_mode", {})
    if not isinstance(attempts, dict):
        return 0
    value = attempts.get(mode, 0)
    return int(value) if isinstance(value, (int, float)) else 0


def _mode_reward(summary: dict[str, Any], mode: str) -> float:
    rewards = summary.get("reward_by_mode", {})
    if not isinstance(rewards, dict):
        return 0.0
    value = rewards.get(mode, 0)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _fixed_choice(*, ratio: Decimal, summary: dict[str, Any]) -> str:
    if ratio <= 0:
        return "exploit"
    if ratio >= 1:
        return "explore"
    explore_attempts = _mode_attempts(summary, "explore")
    exploit_attempts = _mode_attempts(summary, "exploit")
    total = explore_attempts + exploit_attempts
    if total == 0:
        return "explore" if ratio >= Decimal("0.5") else "exploit"
    current_share = Decimal(explore_attempts) / Decimal(total)
    return "explore" if current_share < ratio else "exploit"


def _average_reward(summary: dict[str, Any], mode: str) -> float:
    attempts = _mode_attempts(summary, mode)
    if attempts <= 0:
        return 0.0
    return _mode_reward(summary, mode) / attempts


def _epsilon_greedy_choice(*, ratio: Decimal, summary: dict[str, Any]) -> str:
    budget_choice = _fixed_choice(ratio=ratio, summary=summary)
    explore_attempts = _mode_attempts(summary, "explore")
    exploit_attempts = _mode_attempts(summary, "exploit")
    if explore_attempts == 0 and ratio > 0:
        return "explore"
    if exploit_attempts == 0 and ratio < 1:
        return "exploit"
    if budget_choice == "explore":
        return "explore"
    explore_score = _average_reward(summary, "explore")
    exploit_score = _average_reward(summary, "exploit")
    if explore_score > exploit_score:
        return "explore"
    if exploit_score > explore_score:
        return "exploit"
    return budget_choice


def _ucb_score(summary: dict[str, Any], mode: str, *, ratio: Decimal) -> float:
    attempts = _mode_attempts(summary, mode)
    total = _mode_attempts(summary, "explore") + _mode_attempts(summary, "exploit")
    if attempts == 0:
        return float("inf")
    average = _average_reward(summary, mode)
    base_bonus = math.sqrt(2.0 * math.log(max(total, 1)) / attempts)
    if mode == "explore":
        bonus_scale = 1.0 + float(ratio)
    else:
        bonus_scale = 1.0 + float(Decimal("1") - ratio)
    return average + bonus_scale * base_bonus


def decide_selection_mode(
    *,
    strategy_policy: str,
    exploration_ratio: Any,
    orchestration_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    policy = normalize_strategy_policy(strategy_policy)
    ratio = normalize_exploration_ratio(exploration_ratio)
    summary = clone_orchestration_summary(orchestration_summary)

    if policy == "fixed":
        selected = _fixed_choice(ratio=ratio, summary=summary)
        rationale = "share_budget"
    elif policy == "epsilon_greedy":
        selected = _epsilon_greedy_choice(ratio=ratio, summary=summary)
        rationale = "budget_then_average_reward"
    else:
        if ratio <= 0:
            selected = "exploit"
            rationale = "zero_exploration_ratio"
        elif ratio >= 1:
            selected = "explore"
            rationale = "full_exploration_ratio"
        else:
            explore_score = _ucb_score(summary, "explore", ratio=ratio)
            exploit_score = _ucb_score(summary, "exploit", ratio=ratio)
            selected = "explore" if explore_score >= exploit_score else "exploit"
            rationale = "ucb_reward_plus_uncertainty"

    explore_attempts = _mode_attempts(summary, "explore")
    exploit_attempts = _mode_attempts(summary, "exploit")
    total_attempts = explore_attempts + exploit_attempts
    actual_ratio = (
        Decimal(explore_attempts) / Decimal(total_attempts)
        if total_attempts > 0
        else Decimal("0")
    )
    return {
        "selection_mode": selected,
        "strategy_policy": policy,
        "target_exploration_ratio": format(ratio, "f"),
        "actual_exploration_ratio": format(actual_ratio, "f"),
        "rationale": rationale,
        "attempts_by_mode": dict(summary["attempts_by_mode"]),
        "reward_by_mode": dict(summary["reward_by_mode"]),
        "keeps_by_mode": dict(summary["keeps_by_mode"]),
        "non_keeps_by_mode": dict(summary["non_keeps_by_mode"]),
    }
