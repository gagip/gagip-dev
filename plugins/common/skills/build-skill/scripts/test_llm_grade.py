"""LLM 채점의 입력 조립·응답 파싱·실패 처리를 가짜 claude 응답으로 확인한다. 실제 호출 없음."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import unittest.mock

import _llm_grade
from _harness import RunResult, snapshot_files

RUBRIC = """# 검수 기준

| # | 기준 | 통과 조건 |
|---|---|---|
| 1 | 요청을 지켰나 | 요청한 파일만 썼다 |
| 2 | 근거가 있나 | 단정마다 근거가 있다 |
"""


def answer(text: str, *, is_error: bool = False):
    """가짜 claude: 채점자 응답 text를 돌려주는 runner와 받은 인자를 기록할 목록."""
    seen = []

    def runner(prompt, workdir, **kwargs):
        seen.append({"prompt": prompt, **kwargs})
        return [{"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}},
                {"type": "result", "is_error": is_error, "num_turns": 1, "duration_ms": 50,
                 "usage": {"input_tokens": 7, "output_tokens": 3}}]
    return runner, seen


def items(*pairs):
    return json.dumps({"items": [{"no": n, "passed": p, "quote": f"인용{n}", "fix": "" if p else f"고칠{n}"}
                                 for n, p in pairs]}, ensure_ascii=False)


class GradeRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.skill = root / "skill"
        (self.skill / "references").mkdir(parents=True)
        (self.skill / "references" / "review-rubric.md").write_text(RUBRIC, encoding="utf-8")
        work = root / "work"
        work.mkdir()
        (work / "old.md").write_text("원래 있던 파일", encoding="utf-8")
        self.run = RunResult(True, final_text="다 썼다", workdir=work, snapshot=snapshot_files(work))
        (work / "docs").mkdir()
        (work / "docs" / "plan.md").write_text("새 계획서 본문", encoding="utf-8")

    def grade(self, runner):
        return _llm_grade.grade_run(self.run, skill_dir=self.skill, request="계획서 써줘",
                                    model="sonnet", timeout=60, runner=runner)

    def test_success_reads_every_item_and_cost(self):
        runner, seen = answer("채점 결과:\n```json\n" + items((1, True), (2, False)) + "\n```")
        g = self.grade(runner)
        self.assertEqual("", g.error)
        self.assertEqual([2], g.failed_nos)
        self.assertFalse(g.passed_all)
        self.assertEqual("고칠2", g.items[1].fix)
        self.assertEqual(10, g.cost.tokens)

    def test_prompt_has_request_rubric_and_only_changed_files(self):
        runner, seen = answer(items((1, True), (2, True)))
        self.grade(runner)
        prompt = seen[0]["prompt"]
        self.assertIn("계획서 써줘", prompt)
        self.assertIn("요청한 파일만 썼다", prompt)
        self.assertIn("새 계획서 본문", prompt)
        self.assertIn("다 썼다", prompt)
        self.assertNotIn("원래 있던 파일", prompt)

    def test_grader_runs_without_tools_or_user_settings(self):
        runner, seen = answer(items((1, True), (2, True)))
        self.grade(runner)
        args = seen[0]["extra_args"]
        self.assertEqual("", args[args.index("--tools") + 1])
        self.assertIn("--strict-mcp-config", args)
        self.assertEqual("sonnet", seen[0]["model"])

    def test_broken_json_is_a_grading_failure(self):
        runner, _ = answer('{"items": [ {"no": 1,')
        self.assertTrue(self.grade(runner).error.startswith("JSON"))

    def test_missing_or_unknown_item_is_a_grading_failure(self):
        runner, _ = answer(items((1, True), (3, True)))
        error = self.grade(runner).error
        self.assertIn("누락 [2]", error)
        self.assertIn("없는 번호 [3]", error)

    def test_error_result_is_a_grading_failure(self):
        runner, _ = answer(items((1, True), (2, True)), is_error=True)
        self.assertEqual("채점 호출이 오류로 끝남", self.grade(runner).error)

    def test_timeout_is_a_grading_failure(self):
        def runner(prompt, workdir, **kwargs):
            raise subprocess.TimeoutExpired(["claude"], kwargs["timeout"])
        self.assertEqual("시간 초과 60초", self.grade(runner).error)

    def test_os_error_is_a_grading_failure(self):
        def runner(prompt, workdir, **kwargs):
            raise OSError(7, "Argument list too long")
        self.assertIn("호출 실패", self.grade(runner).error)

    def test_missing_rubric(self):
        (self.skill / "references" / "review-rubric.md").unlink()
        runner, seen = answer("")
        self.assertIn("루브릭 없음", self.grade(runner).error)
        self.assertEqual([], seen)

    def test_long_artifacts_are_cut(self):
        (self.run.workdir / "big.md").write_text("가" * (_llm_grade.MAX_ARTIFACT_CHARS + 10), encoding="utf-8")
        text = _llm_grade.collect_artifacts(self.run)
        self.assertLessEqual(len(text), _llm_grade.MAX_ARTIFACT_CHARS + 100)
        self.assertIn("잘랐다", text)


class SummarizeTests(unittest.TestCase):
    def g(self, *failed, error=""):
        return _llm_grade.Grade(items=[_llm_grade.GradeItem(n, n not in failed) for n in (1, 2, 3)], error=error)

    def test_counts_passes_and_failed_items(self):
        line = _llm_grade.summarize([self.g(), self.g(2), self.g(2, 3)])
        self.assertEqual("LLM 1/3 통과(미통과 #2×2, #3×1)", line)

    def test_grading_failures_and_skipped_runs(self):
        line = _llm_grade.summarize([self.g(), None, _llm_grade.Grade(error="JSON 없음")])
        self.assertEqual("LLM 1/1 통과 · 채점 실패 1: JSON 없음", line)

    def test_nothing_graded(self):
        self.assertEqual("LLM 채점 대상 run 없음", _llm_grade.summarize([None]))


class GradeCaseTests(unittest.TestCase):
    """run_skill_test._grade_case: 어떤 run을 채점하고 요약을 어떻게 내는가."""

    def setUp(self):
        import argparse
        import run_skill_test
        from _harness import Case, CaseResult
        self.mod = run_skill_test
        self.args = argparse.Namespace(no_llm_grade=False, grader_model="sonnet", timeout=60)
        self.case = Case("c", Path("c.py"), "요청", 3, "", "bypassPermissions", lambda ctx: None, grader="llm")
        self.cr = CaseResult("c", [RunResult(True), RunResult(False), RunResult(False, error=True)])

    def test_only_structurally_passing_runs_are_graded(self):
        graded = []

        def fake(run, **kw):
            graded.append(run)
            return _llm_grade.Grade(items=[_llm_grade.GradeItem(1, True)])

        with unittest.mock.patch.object(self.mod, "grade_run", fake):
            grades, summary = self.mod._grade_case(Path("."), self.case, self.cr, self.args)
        self.assertEqual([self.cr.runs[0]], graded)
        self.assertEqual([True, False, False], [g is not None for g in grades])
        self.assertEqual("LLM 1/1 통과", summary)

    def test_disabled_grading_calls_nothing(self):
        self.args.no_llm_grade = True
        with unittest.mock.patch.object(self.mod, "grade_run", side_effect=AssertionError("호출됨")):
            grades, summary = self.mod._grade_case(Path("."), self.case, self.cr, self.args)
        self.assertEqual([], grades)
        self.assertIn("--no-llm-grade", summary)

    def test_code_grader_is_untouched(self):
        self.case.grader = "code"
        self.assertEqual(([], None), self.mod._grade_case(Path("."), self.case, self.cr, self.args))


class RubricNumbersTests(unittest.TestCase):
    def test_reads_table_rows(self):
        self.assertEqual([1, 2], _llm_grade.rubric_item_numbers(RUBRIC))

    def test_every_llm_graded_case_has_a_rubric(self):
        from _harness import load_case
        skills = Path(__file__).resolve().parents[2]
        llm_cases = [p for p in skills.glob("*/evals/*.py") if load_case(p).grader == "llm"]
        self.assertTrue(llm_cases)
        for p in llm_cases:
            with self.subTest(case=f"{p.parent.parent.name}/{p.stem}"):
                self.assertTrue((p.parent.parent / _llm_grade.RUBRIC_PATH).is_file())

    def test_repo_rubrics_have_items(self):
        skills = Path(__file__).resolve().parents[2]
        for rubric in skills.glob("*/references/review-rubric.md"):
            with self.subTest(rubric=rubric.parent.parent.name):
                self.assertTrue(_llm_grade.rubric_item_numbers(rubric.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
