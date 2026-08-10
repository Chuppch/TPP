from __future__ import annotations

import contextlib
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts import run_benchmarks, run_experiment_pipeline, verify_results
from scripts.experiment_common import RAW_FIELDS


ROOT = Path(__file__).resolve().parents[2]
PAPER_INSTANCE = ROOT / "examples" / "paper_four_market.json"


class ExperimentPipelineTests(unittest.TestCase):
    def test_pipeline_generates_raw_tables_report_and_figures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "experiment"
            exit_code = run_experiment_pipeline.main(
                [
                    str(PAPER_INSTANCE),
                    "--output-dir",
                    str(output),
                    "--seeds",
                    "0,1",
                    "--k-max",
                    "2",
                    "--lambda-max",
                    "1",
                    "--alpha",
                    "0.5",
                    "--exact-small",
                ]
            )

            self.assertEqual(exit_code, 0)
            with (output / "raw_results.csv").open(
                "r", encoding="utf-8", newline=""
            ) as stream:
                raw_rows = list(csv.DictReader(stream))
            self.assertEqual(len(raw_rows), 2)
            self.assertEqual({row["seed"] for row in raw_rows}, {"0", "1"})
            self.assertTrue(all(float(row["total_cost"]) == 121 for row in raw_rows))
            self.assertTrue(all(float(row["gap_percent"]) == 0 for row in raw_rows))

            with (output / "summary.csv").open(
                "r", encoding="utf-8", newline=""
            ) as stream:
                summary = next(csv.DictReader(stream))
            self.assertEqual(summary["runs"], "2")
            self.assertEqual(float(summary["mean_cost"]), 121)
            self.assertEqual(float(summary["cost_stdev"]), 0)

            report = json.loads((output / "verification.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["valid_rows"], 2)

            expected_figures = {
                "mean_cost_comparison.svg",
                "gap_comparison.svg",
                "runtime_comparison.svg",
                "seed_stability.svg",
            }
            actual_figures = {path.name for path in (output / "figures").glob("*.svg")}
            self.assertEqual(actual_figures, expected_figures)
            for filename in expected_figures:
                content = (output / "figures" / filename).read_text(encoding="utf-8")
                self.assertIn("<svg", content)
                self.assertIn("</svg>", content)

    def test_runner_refuses_to_exceed_run_safety_cap(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = run_benchmarks.main(
                [
                    str(PAPER_INSTANCE),
                    "--seeds",
                    "0,1",
                    "--max-runs",
                    "1",
                ]
            )
        self.assertEqual(exit_code, 2)
        self.assertIn("Safety cap exceeded", stderr.getvalue())

    def test_verifier_rejects_a_tampered_cost(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "raw.csv"
            run_exit = run_benchmarks.main(
                [
                    str(PAPER_INSTANCE),
                    "--output",
                    str(raw),
                    "--seeds",
                    "0",
                    "--k-max",
                    "1",
                    "--exact-small",
                ]
            )
            self.assertEqual(run_exit, 0)
            with raw.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            rows[0]["total_cost"] = "999"
            with raw.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=RAW_FIELDS)
                writer.writeheader()
                writer.writerows(rows)

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                verify_exit = verify_results.main([str(raw)])
            self.assertEqual(verify_exit, 1)
            self.assertIn("total_cost mismatch", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
