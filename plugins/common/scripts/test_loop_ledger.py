import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import loop_ledger  # noqa: E402

GUARDS = "확정 목록,심각도 근거"


class LoopLedgerTest(unittest.TestCase):
    def setUp(self):
        self.ledger = str(Path(tempfile.mkdtemp()) / "ledger.json")

    def run_cmd(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = loop_ledger.main([argv[0], self.ledger, *argv[1:]])
        return code, out.getvalue()

    def close_round(self, high, medium):
        for g in GUARDS.split(","):
            self.run_cmd("guard", g, "--quiet")
        return self.run_cmd("end", "--high", str(high), "--medium", str(medium))

    def test_stops_when_findings_remain_at_round_cap(self):
        self.run_cmd("init", "--max-rounds", "2", "--guards", GUARDS)
        for _ in range(2):
            self.run_cmd("start")
            code, out = self.close_round(1, 0)
        self.assertEqual(code, loop_ledger.STOP)
        self.assertIn("상한", out)
        self.assertEqual(self.run_cmd("start")[0], loop_ledger.STOP)

    def test_ends_when_no_high_or_medium(self):
        self.run_cmd("init", "--max-rounds", "3", "--guards", GUARDS)
        self.run_cmd("start")
        code, out = self.close_round(0, 0)
        self.assertEqual(code, 0)
        self.assertIn("끝", out)
        with self.assertRaises(ValueError):
            self.run_cmd("start")

    def test_low_finding_is_never_applied(self):
        self.run_cmd("init", "--max-rounds", "3", "--guards", GUARDS)
        self.run_cmd("start")
        code, out = self.run_cmd("check", "key.new", "--severity", "low")
        self.assertEqual(code, 0)
        self.assertIn("반영 안 함", out)

    def test_negative_counts_rejected(self):
        self.run_cmd("init", "--max-rounds", "3", "--guards", GUARDS)
        self.run_cmd("start")
        for g in GUARDS.split(","):
            self.run_cmd("guard", g, "--quiet")
        with self.assertRaises(ValueError):
            self.run_cmd("end", "--high", "-1", "--medium", "1")

    def test_cli_exits_2_on_misuse(self):
        script = str(Path(loop_ledger.__file__))
        subprocess.run([sys.executable, script, "init", self.ledger, "--max-rounds", "3", "--guards", GUARDS], check=True,
                       capture_output=True)
        for argv in (["init", self.ledger, "--max-rounds", "3", "--guards", GUARDS],
                     ["guard", self.ledger, "없는 장치", "--quiet"]):
            if argv[0] == "guard":
                subprocess.run([sys.executable, script, "start", self.ledger], check=True, capture_output=True)
            self.assertEqual(subprocess.run([sys.executable, script, *argv], capture_output=True).returncode, 2, argv)

    def test_target_changed_earlier_is_held_unless_high(self):
        self.run_cmd("init", "--max-rounds", "3", "--guards", GUARDS)
        self.run_cmd("start")
        self.run_cmd("change", "key.a")
        self.close_round(1, 0)
        self.run_cmd("start")
        self.assertEqual(self.run_cmd("check", "key.b", "--severity", "medium")[0], 0)
        code, out = self.run_cmd("check", "key.a", "--severity", "medium")
        self.assertEqual(code, 0)
        self.assertIn("반영 안 함", out)
        self.assertEqual(self.run_cmd("check", "key.a", "--severity", "high")[0], loop_ledger.STOP)

    def test_second_change_of_same_target_stops_without_approval(self):
        self.run_cmd("init", "--max-rounds", "3", "--guards", GUARDS)
        self.run_cmd("start")
        self.run_cmd("change", "key.a")
        self.close_round(1, 0)
        self.run_cmd("start")
        self.assertEqual(self.run_cmd("change", "key.a")[0], loop_ledger.STOP)
        self.assertEqual(self.run_cmd("change", "key.a", "--approved")[0], 0)

    def test_round_cannot_close_with_unrecorded_guard(self):
        self.run_cmd("init", "--max-rounds", "3", "--guards", GUARDS)
        self.run_cmd("start")
        self.run_cmd("guard", "확정 목록", "--fired", "--note", "중간 2건 막음")
        with self.assertRaises(ValueError):
            self.run_cmd("end", "--high", "0", "--medium", "0")

    def test_report_lists_guards_per_round(self):
        self.run_cmd("init", "--max-rounds", "3", "--guards", GUARDS)
        self.run_cmd("start")
        self.run_cmd("guard", "확정 목록", "--fired", "--note", "중간 2건 막음")
        self.run_cmd("guard", "심각도 근거", "--quiet")
        self.run_cmd("end", "--high", "0", "--medium", "1")
        _, out = self.run_cmd("report")
        self.assertIn("| 확정 목록 | 걸림: 중간 2건 막음 |", out)
        self.assertIn("| 판정 | 다음 회차 |", out)


if __name__ == "__main__":
    unittest.main()
