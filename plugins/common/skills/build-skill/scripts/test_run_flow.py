"""러너 흐름: 판정 뒤 산출물 저장·임시 폴더 정리, 예외 때 정리, all_ok(종료 코드)의 뜻. claude 호출 없음."""
import argparse
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import _harness
import run_skill_test
from _harness import Case, CaseResult, RunResult
from _verdict import Judgement, Verdict


def workdir(root: Path, name: str) -> Path:
    d = root / name
    d.mkdir()
    return d


class RunSkillFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.skill = root / "demo"
        (self.skill / "evals").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("x", encoding="utf-8")
        (self.skill / "evals" / "c.py").write_text('PROMPT = "p"\ndef check(ctx):\n    pass\n', encoding="utf-8")
        self.root = root
        self.args = argparse.Namespace(
            case=None, model=None, runs=None, baseline=False, max_turns=1, timeout=1, keep_temp=False,
            threshold=1.0, no_llm_grade=True, grader_model="sonnet", run_root=root / "runs")

    def run_skill(self, *passed: bool):
        self.works = [workdir(self.root, f"w{i}") for i in range(len(passed))]
        runs = [RunResult(p, workdir=w) for p, w in zip(passed, self.works)]
        with mock.patch.object(run_skill_test, "run_case", lambda *a, **k: CaseResult("c", runs)), \
                contextlib.redirect_stderr(io.StringIO()):
            return run_skill_test._run_skill(self.skill, self.args)

    def test_fail_saves_artifacts_then_removes_workdirs(self):
        [o] = self.run_skill(False)
        self.assertIs(Verdict.FAIL, o.judgement.verdict)
        self.assertTrue((self.args.run_root / "demo" / "c" / "case.json").is_file())
        self.assertFalse(self.works[0].exists())

    def test_review_is_saved_too(self):
        self.args.threshold = 0.5
        [o] = self.run_skill(True, False)
        self.assertIs(Verdict.REVIEW, o.judgement.verdict)
        self.assertTrue((self.args.run_root / "demo" / "c" / "run2" / "result.json").is_file())

    def test_pass_saves_nothing_but_still_cleans(self):
        [o] = self.run_skill(True)
        self.assertIs(Verdict.PASS, o.judgement.verdict)
        self.assertFalse(self.args.run_root.exists())
        self.assertFalse(self.works[0].exists())

    def test_keep_temp_keeps_workdir(self):
        self.args.keep_temp = True
        self.run_skill(False)
        self.assertTrue(self.works[0].exists())

    def test_workdir_removed_even_if_saving_fails(self):
        with mock.patch.object(run_skill_test, "save_case", side_effect=OSError("디스크 가득")):
            with self.assertRaises(OSError):
                self.run_skill(False)
        self.assertFalse(self.works[0].exists())


class Loader:
    def claude_args(self, with_skill):
        return []


class ExceptionCleanupTests(unittest.TestCase):
    """run 도중 예외가 나도 임시 폴더가 남지 않는다(RunResult가 호출자에게 가지 않는 경로)."""

    def setUp(self):
        self.made: list[Path] = []
        real = tempfile.mkdtemp

        def track(*a, **k):
            self.made.append(Path(real(*a, **k)))
            return str(self.made[-1])
        patcher = mock.patch.object(_harness.tempfile, "mkdtemp", track)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.case = Case("c", Path("c.py"), "p", 2, "", "bypassPermissions", lambda ctx: None)

    def test_exception_inside_one_run_removes_its_tempdir(self):
        with mock.patch.object(_harness, "run_claude", side_effect=ValueError("예상 못 한 오류")):
            with self.assertRaises(ValueError):
                _harness._one_run(self.case, Loader(), with_skill=True, model=None, max_turns=1, timeout=1,
                                  keep_temp=False)
        self.assertEqual(1, len(self.made))
        self.assertFalse(self.made[0].exists())

    def test_exception_in_a_later_run_removes_earlier_runs(self):
        first = [True]

        def one_run(case, loader, **kw):
            if first.pop() if first else False:
                return RunResult(True, workdir=Path(tempfile.mkdtemp()))
            raise ValueError("두 번째 run에서 터짐")

        class FakeLoader:
            def __init__(self, skill_dir): pass
            def __enter__(self): return Loader()
            def __exit__(self, *exc): return False

        with mock.patch.object(_harness, "_one_run", one_run), \
                mock.patch.object(_harness, "SkillLoader", FakeLoader):
            with self.assertRaises(ValueError):
                _harness.run_case(Path("."), self.case, baseline=False, model=None, max_turns=1, timeout=1,
                                  keep_temp=False)
        self.assertEqual(1, len(self.made))
        self.assertFalse(self.made[0].exists())


class AllOkTests(unittest.TestCase):
    """all_ok가 거짓이면 종료 코드 1이다. REVIEW만 있으면 참이어야 한다."""

    def outcome(self, verdict: Verdict):
        case = Case("c", Path("c.py"), "p", 1, "", "bypassPermissions", lambda ctx: None)
        return run_skill_test.Outcome(case, CaseResult("c", [RunResult(True)]), Judgement(verdict, ""))

    def payload(self, *verdicts):
        return run_skill_test._skill_payload(Path("/s/demo"), [self.outcome(v) for v in verdicts])

    def test_review_only_is_ok(self):
        self.assertTrue(self.payload(Verdict.REVIEW, Verdict.PASS)["all_ok"])

    def test_any_fail_is_not_ok(self):
        self.assertFalse(self.payload(Verdict.REVIEW, Verdict.FAIL)["all_ok"])

    def test_case_keys_read_by_release_check(self):
        case = self.payload(Verdict.REVIEW)["cases"][0]
        self.assertLessEqual({"case", "verdict", "reason", "grader", "pass", "total", "runs"}, set(case))
        self.assertEqual("REVIEW", case["verdict"])


if __name__ == "__main__":
    unittest.main()
