import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tokenbench
from adapters import AdapterUnavailable, rtk_cli, toon_enc
from make_matrix import format_cell


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tokenbench.py"


class TokenbenchCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(RUNNER), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def test_baseline_runs_with_only_core_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--tools",
                    "baseline",
                    "--seeds",
                    "1",
                    "--output-dir",
                    tmp,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads((Path(tmp) / "baseline.json").read_text())
            self.assertEqual(payload["tool"], "baseline")

    def test_invalid_input_fails_before_creating_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "new-results"
            for args, expected in (
                (("--tools", "missing", "--output-dir", str(output_dir)), "unknown adapter"),
                (("--tools", "baseline", "--lanes", "missing", "--output-dir", str(output_dir)), "unknown lane"),
                (("--tools", "baseline", "--seeds", "0", "--output-dir", str(output_dir)), "positive integer"),
            ):
                result = self.run_cli(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)
                self.assertFalse(output_dir.exists())

    def test_partial_and_total_failures_are_explicit(self):
        def corpus(_seed):
            return "token", [("extract", "token")]

        calls = 0

        def flaky(_text):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise AdapterUnavailable("temporary tool failure")
            return "token"

        with patch.object(tokenbench, "CONTENTS", {"sample": corpus}):
            partial = tokenbench.run_tool("flaky", flaky, 3)[0]
            failed = tokenbench.run_tool("failed", lambda _text: (_ for _ in ()).throw(AdapterUnavailable("not installed")), 2)[0]

        self.assertEqual(partial["status"], "degraded")
        self.assertEqual((partial["attempts"], partial["successes"], partial["errors"]), (3, 2, 1))
        self.assertIn("temporary tool failure", partial["error_summary"])
        self.assertEqual(failed["status"], "failed")
        self.assertEqual((failed["attempts"], failed["successes"], failed["errors"]), (2, 0, 2))
        self.assertIn("not installed", failed["error_summary"])

    def test_toon_does_not_fall_back_when_node_is_unavailable(self):
        with patch("adapters.configured_executable", side_effect=AdapterUnavailable("node is unavailable")):
            with self.assertRaisesRegex(AdapterUnavailable, "node is unavailable"):
                toon_enc('{"name": "tokenbench"}')

    def test_rtk_does_not_fall_back_when_the_command_fails(self):
        failed_process = subprocess.CompletedProcess(["rtk"], 1, stdout="", stderr="missing config")
        with patch("subprocess.run", return_value=failed_process):
            with self.assertRaisesRegex(AdapterUnavailable, "rtk failed"):
                rtk_cli("plain text")

    def test_matrix_marks_partial_adapter_failures(self):
        record = {
            "reduction_mean": 50.0,
            "survival": {"extract": 100},
            "errors": 1,
            "successes": 2,
            "attempts": 3,
        }
        self.assertEqual(format_cell(record), "50% / fid 100% ⚠ 2/3")
        legacy_record = {"reduction_mean": 50.0, "survival": {"extract": 100}, "errors": 1}
        self.assertEqual(format_cell(legacy_record), "50% / fid 100%")


if __name__ == "__main__":
    unittest.main()
