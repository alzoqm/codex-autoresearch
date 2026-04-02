from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ..base import AutoresearchScriptsTestBase


class AutoresearchResearchFlowTest(AutoresearchScriptsTestBase):
    maxDiff = None

    def test_research_first_init_persists_phase_and_knowledge_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            results_path = tmpdir / "research-results.tsv"
            state_path = tmpdir / "autoresearch-state.json"

            result = self.run_script(
                "autoresearch_init_run.py",
                "--results-path",
                str(results_path),
                "--state-path",
                str(state_path),
                "--mode",
                "loop",
                "--goal",
                "Research-first optimization",
                "--scope",
                "src/**/*.py",
                "--metric-name",
                "score",
                "--direction",
                "higher",
                "--verify",
                "python3 -c pass",
                "--research-mode",
                "research_first",
                "--exploration-phase-budget",
                "4",
                "--min-sources",
                "6",
                "--min-hypotheses",
                "3",
                "--baseline-metric",
                "10",
                "--baseline-commit",
                "base111",
                "--baseline-description",
                "baseline score",
            )

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(result["research_mode"], "research_first")
            self.assertEqual(result["phase"], "exploration")
            self.assertEqual(state["config"]["research_mode"], "research_first")
            self.assertEqual(state["state"]["phase"], "exploration")
            self.assertEqual(state["state"]["exploration"]["budget_iterations"], 4)
            self.assertEqual(state["state"]["exploration"]["min_sources"], 6)
            self.assertEqual(state["state"]["exploration"]["min_hypotheses"], 3)
            self.assertTrue(state["state"]["knowledge"]["sources_summary_path"].endswith("research-sources.md"))
            self.assertTrue(state["state"]["knowledge"]["hypothesis_registry_path"].endswith("hypothesis-registry.json"))

    def test_collect_sources_generate_hypotheses_and_write_report_update_state(self) -> None:
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
                "Research-first optimization",
                "--scope",
                "src/**/*.py",
                "--metric-name",
                "score",
                "--direction",
                "higher",
                "--verify",
                "python3 -c pass",
                "--research-mode",
                "research_first",
                "--baseline-metric",
                "10",
                "--baseline-commit",
                "base111",
                "--baseline-description",
                "baseline score",
            )

            source_result = self.run_script(
                "autoresearch_collect_sources.py",
                "--results-path",
                str(results_path),
                "--state-path",
                str(state_path),
                "--source-id",
                "paper-a",
                "--title",
                "Paper A",
                "--url",
                "https://example.com/paper-a",
                "--source-type",
                "papers",
                "--summary",
                "first finding||second finding",
                "--query",
                "query a",
            )
            self.assertEqual(source_result["source_ids"], ["s-paper-a"])
            self.assertTrue((tmpdir / "research-sources.md").exists())
            self.assertTrue((tmpdir / "research-corpus.jsonl").exists())

            hypothesis_result = self.run_script(
                "autoresearch_generate_hypotheses.py",
                "--state-path",
                str(state_path),
                "--hypothesis-id",
                "idea-1",
                "--title",
                "Idea 1",
                "--statement",
                "Try an evidence-backed strategy",
                "--source-ids",
                "s-paper-a",
                "--strategy-family",
                "paper-backed",
                "--expected-effect",
                "higher keep rate",
                "--verify-plan",
                "measure score",
                "--guard-plan",
                "tests pass",
                "--cost",
                "medium",
                "--risk",
                "low",
            )
            self.assertEqual(hypothesis_result["hypothesis_ids"], ["h-idea-1"])
            self.assertTrue((tmpdir / "hypothesis-registry.json").exists())

            report_result = self.run_script(
                "autoresearch_write_experiment_report.py",
                "--state-path",
                str(state_path),
                "--experiment-id",
                "4",
                "--hypothesis-id",
                "idea-1",
                "--iteration",
                "1",
                "--outcome",
                "keep",
                "--metric-before",
                "10",
                "--metric-after",
                "12",
                "--summary",
                "Improved score with grounded change",
                "--source-id",
                "paper-a",
                "--code-change",
                "Adjusted runtime selection",
                "--reflection",
                "Grounded hypotheses improved targeting",
                "--next-step",
                "Queue the next ranked idea",
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(report_result["hypothesis_id"], "h-idea-1")
            self.assertEqual(state["state"]["active_hypothesis_id"], "h-idea-1")
            self.assertTrue(state["state"]["last_report_path"].endswith("EXP-4.md"))
            self.assertEqual(state["state"]["phase"], "exploitation")
            self.assertEqual(
                state["state"]["reflection_summary"],
                ["Grounded hypotheses improved targeting"],
            )
            self.assertTrue((tmpdir / "experiment-reports" / "EXP-4.md").exists())

    def test_generate_hypotheses_prioritizes_ranked_entries_for_active_queue(self) -> None:
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
                "Research-first optimization",
                "--scope",
                "src/**/*.py",
                "--metric-name",
                "score",
                "--direction",
                "higher",
                "--verify",
                "python3 -c pass",
                "--research-mode",
                "research_first",
                "--baseline-metric",
                "10",
                "--baseline-commit",
                "base111",
                "--baseline-description",
                "baseline score",
            )

            result = self.run_script(
                "autoresearch_generate_hypotheses.py",
                "--state-path",
                str(state_path),
                "--hypothesis-id",
                "idea-queued",
                "--title",
                "Queued first",
                "--statement",
                "Try the lower-priority idea first",
                "--source-ids",
                "s-paper-a",
                "--strategy-family",
                "queued-family",
                "--expected-effect",
                "small gain",
                "--verify-plan",
                "measure score",
                "--guard-plan",
                "tests pass",
                "--cost",
                "low",
                "--risk",
                "low",
                "--status",
                "queued",
                "--hypothesis-id",
                "idea-ranked",
                "--title",
                "Ranked later",
                "--statement",
                "Prefer the explicitly ranked idea",
                "--source-ids",
                "s-paper-b",
                "--strategy-family",
                "ranked-family",
                "--expected-effect",
                "larger gain",
                "--verify-plan",
                "measure score",
                "--guard-plan",
                "tests pass",
                "--cost",
                "low",
                "--risk",
                "low",
                "--status",
                "ranked",
            )

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(
                result["queued_hypothesis_ids"],
                ["h-idea-ranked", "h-idea-queued"],
            )
            self.assertEqual(state["state"]["queued_hypothesis_ids"], ["h-idea-ranked", "h-idea-queued"])
            self.assertEqual(state["state"]["active_hypothesis_id"], "h-idea-ranked")

    def test_record_iteration_persists_hypothesis_and_report_metadata(self) -> None:
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
                "Research-first optimization",
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

            result = self.run_script(
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
                "--phase",
                "exploitation",
                "--hypothesis-id",
                "idea-2",
                "--source-id",
                "paper-a",
                "--report-path",
                str(tmpdir / "experiment-reports" / "EXP-2.md"),
                "--reflection",
                "This path improved score cleanly",
                "--description",
                "tested ranked idea",
            )

            log_text = results_path.read_text(encoding="utf-8")
            self.assertIn("hypothesis-id/idea-2", log_text)
            self.assertIn("source-id/paper-a", log_text)
            self.assertEqual(result["active_hypothesis_id"], "idea-2")
            self.assertTrue(result["last_report_path"].endswith("EXP-2.md"))
