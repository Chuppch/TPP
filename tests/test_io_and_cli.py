from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tpp.cli import main
from tpp.io import load_instance


ROOT = Path(__file__).resolve().parents[1]
PAPER_INSTANCE = ROOT / "examples" / "paper_four_market.json"


class IOAndCLITests(unittest.TestCase):
    def test_load_instance_reads_paper_json(self) -> None:
        instance = load_instance(PAPER_INSTANCE)
        self.assertEqual(instance.name, "paper-four-market-asymmetric")
        self.assertEqual(instance.market_count, 4)
        self.assertEqual(instance.item_count, 3)
        self.assertEqual(instance.travel_costs[0][4], 16)
        self.assertEqual(instance.purchase_costs[3][0], 23)

    def test_load_instance_rejects_non_object_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "list-root.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "root must be an object"):
                load_instance(path)

    def test_load_instance_rejects_missing_required_field(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing-field.json"
            path.write_text(json.dumps({"travel_costs": [[0, 1], [1, 0]]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "market_purchase_costs"):
                load_instance(path)

    def test_exact_command_prints_paper_optimum(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["exact", str(PAPER_INSTANCE)])
        self.assertEqual(exit_code, 0)
        self.assertIn("route: 0 -> 3 -> 2 -> 0", stdout.getvalue())
        self.assertIn("total_cost: 121", stdout.getvalue())

    def test_solve_command_can_emit_json(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "solve",
                    str(PAPER_INSTANCE),
                    "--k-max",
                    "2",
                    "--lambda-max",
                    "1",
                    "--alpha",
                    "0.5",
                    "--seed",
                    "0",
                    "--json",
                ]
            )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["total_cost"], 121)
        self.assertEqual(payload["iterations"], 2)
        self.assertEqual(payload["seed"], 0)

    def test_cli_reports_missing_file(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = main(["exact", "does-not-exist.json"])
        self.assertEqual(exit_code, 2)
        self.assertIn("error:", stderr.getvalue())

    def test_cli_reports_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformed.json"
            path.write_text("{not-json", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = main(["solve", str(path)])
        self.assertEqual(exit_code, 2)
        self.assertIn("error:", stderr.getvalue())

    def test_cli_reports_invalid_matrix_shape(self) -> None:
        payload = {
            "name": "invalid-matrix",
            "travel_costs": [[0, 1], [1]],
            "market_purchase_costs": [[10]],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid-matrix.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = main(["exact", str(path)])
        self.assertEqual(exit_code, 2)
        self.assertIn("Travel cost matrix must be square", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
