from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ..base import AutoresearchScriptsTestBase


class AutoresearchOrchestrationTest(AutoresearchScriptsTestBase):
    maxDiff = None

    def test_init_persists_orchestration_config_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            results_path = tmpdir / "research-results.tsv"
            state_path = tmpdir / "autoresearch-state.json"

            self.run_script(
                "autoresearch_init_run.py",
                "--results-path",
                str(results_path),
                "--state-path",
                str(state_path),
                "--mode",
                "loop",
                "--goal",
                "Balance exploration and exploitation",
                "--scope",
                "src/**/*.py",
                "--metric-name",
                "score",
                "--direction",
                "higher",
                "--verify",
                "python3 -c pass",
                "--strategy-policy",
                "ucb",
                "--exploration-ratio",
                "0.35",
                "--exploration-source",
                "docs",
                "--exploration-source",
                "papers",
                "--baseline-metric",
                "10",
                "--baseline-commit",
                "base111",
                "--baseline-description",
                "baseline score",
            )

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["config"]["strategy_policy"], "ucb")
            self.assertEqual(state["config"]["exploration_ratio"], "0.35")
            self.assertEqual(state["config"]["exploration_sources"], ["docs", "papers"])
            self.assertEqual(
                state["state"]["orchestration"]["attempts_by_mode"],
                {"explore": 0, "exploit": 0},
            )

            log_text = results_path.read_text(encoding="utf-8")
            self.assertIn("# strategy_policy: ucb", log_text)
            self.assertIn("# exploration_ratio: 0.35", log_text)
            self.assertIn("# exploration_sources: docs, papers", log_text)

    def test_record_iteration_tracks_explore_and_family_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            results_path = tmpdir / "research-results.tsv"
            state_path = tmpdir / "autoresearch-state.json"

            self.run_script(
                "autoresearch_init_run.py",
                "--results-path",
                str(results_path),
                "--state-path",
                str(state_path),
                "--mode",
                "loop",
                "--goal",
                "Improve score",
                "--scope",
                "src/**/*.py",
                "--metric-name",
                "score",
                "--direction",
                "higher",
                "--verify",
                "python3 -c pass",
                "--baseline-metric",
                "10",
                "--baseline-commit",
                "base111",
                "--baseline-description",
                "baseline score",
            )
            self.run_script(
                "autoresearch_record_iteration.py",
                "--results-path",
                str(results_path),
                "--state-path",
                str(state_path),
                "--status",
                "keep",
                "--metric",
                "12",
                "--commit",
                "keep111",
                "--guard",
                "pass",
                "--selection-mode",
                "explore",
                "--strategy-family",
                "paper_idea",
                "--evidence-source",
                "papers",
                "--evidence-source",
                "docs",
                "--description",
                "tried a new strategy family",
            )
            self.run_script(
                "autoresearch_record_iteration.py",
                "--results-path",
                str(results_path),
                "--state-path",
                str(state_path),
                "--status",
                "discard",
                "--metric",
                "11",
                "--commit",
                "drop111",
                "--selection-mode",
                "exploit",
                "--strategy-family",
                "incremental-refactor",
                "--description",
                "local refinement failed",
            )

            state = json.loads(state_path.read_text(encoding="utf-8"))
            orchestration = state["state"]["orchestration"]
            self.assertEqual(orchestration["attempts_by_mode"], {"explore": 1, "exploit": 1})
            self.assertEqual(orchestration["keeps_by_mode"], {"explore": 1, "exploit": 0})
            self.assertEqual(orchestration["non_keeps_by_mode"], {"explore": 0, "exploit": 1})
            self.assertEqual(orchestration["last_selection_mode"], "exploit")
            self.assertEqual(orchestration["last_strategy_family"], "incremental-refactor")
            self.assertEqual(
                orchestration["family_stats"]["paper-idea"]["evidence_sources"],
                ["papers", "docs"],
            )

            log_text = results_path.read_text(encoding="utf-8")
            self.assertIn("[labels: mode/explore, family/paper-idea, source/papers, source/docs]", log_text)
            self.assertIn("[labels: mode/exploit, family/incremental-refactor]", log_text)

    def test_decision_script_uses_ucb_and_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            results_path = tmpdir / "research-results.tsv"
            state_path = tmpdir / "autoresearch-state.json"

            self.run_script(
                "autoresearch_init_run.py",
                "--results-path",
                str(results_path),
                "--state-path",
                str(state_path),
                "--mode",
                "loop",
                "--goal",
                "Improve score",
                "--scope",
                "src/**/*.py",
                "--metric-name",
                "score",
                "--direction",
                "higher",
                "--verify",
                "python3 -c pass",
                "--strategy-policy",
                "ucb",
                "--exploration-ratio",
                "0.4",
                "--baseline-metric",
                "10",
                "--baseline-commit",
                "base111",
                "--baseline-description",
                "baseline score",
            )
            self.run_script(
                "autoresearch_record_iteration.py",
                "--results-path",
                str(results_path),
                "--state-path",
                str(state_path),
                "--status",
                "keep",
                "--metric",
                "12",
                "--commit",
                "keep111",
                "--guard",
                "pass",
                "--selection-mode",
                "exploit",
                "--strategy-family",
                "incremental-refactor",
                "--description",
                "incremental improvement",
            )

            decision = self.run_script(
                "autoresearch_orchestration_decide.py",
                "--results-path",
                str(results_path),
                "--state-path",
                str(state_path),
            )
            self.assertEqual(decision["strategy_policy"], "ucb")
            self.assertEqual(decision["target_exploration_ratio"], "0.4")
            self.assertEqual(decision["attempts_by_mode"], {"explore": 0, "exploit": 1})
            self.assertEqual(decision["selection_mode"], "explore")
