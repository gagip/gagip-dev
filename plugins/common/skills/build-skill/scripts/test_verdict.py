"""판정 규칙(_verdict.judge)을 행마다 고정한다. LLM 호출 없음."""
from pathlib import Path
import unittest

from _harness import Case, CaseResult, RunCost, RunResult
from _verdict import Verdict, judge


def case(**kw) -> Case:
    return Case("c", Path("c.py"), "p", 3, "", "bypassPermissions", lambda ctx: None, **kw)


def run(passed=True, *, error=False, fired=True, turns=10, tokens=1000) -> RunResult:
    return RunResult(passed, reason="" if passed else "check 실패: x", error=error, skill_fired=fired,
                     cost=RunCost(turns=turns, input_tokens=tokens))


def result(runs, baseline=()) -> CaseResult:
    return CaseResult("c", list(runs), baseline=list(baseline))


class VerdictTableTests(unittest.TestCase):
    def verdict(self, c, r, threshold=1.0, **kw):
        return judge(c, r, threshold, **kw)

    def test_all_pass_is_pass(self):
        j = self.verdict(case(), result([run(), run(), run()]))
        self.assertIs(Verdict.PASS, j.verdict)
        self.assertIn("baseline 미실행", j.reason)

    def test_execution_error_is_fail_even_above_threshold(self):
        j = self.verdict(case(), result([run(), run(), run(False, error=True)]), threshold=0.5)
        self.assertIs(Verdict.FAIL, j.verdict)
        self.assertIn("실행 오류 1/3", j.reason)

    def test_below_threshold_is_fail(self):
        j = self.verdict(case(), result([run(), run(False), run(False)]))
        self.assertIs(Verdict.FAIL, j.verdict)
        self.assertIn("통과 1/3 < 임계 1", j.reason)

    def test_no_runs_is_fail(self):
        self.assertIs(Verdict.FAIL, self.verdict(case(), result([])).verdict)

    def test_partial_failure_above_threshold_is_review(self):
        j = self.verdict(case(), result([run(), run(), run(False)]), threshold=0.6)
        self.assertIs(Verdict.REVIEW, j.verdict)
        self.assertIn("통과 2/3", j.reason)

    def test_baseline_passing_as_well_is_review_when_skill_fired(self):
        j = self.verdict(case(), result([run(), run(), run()], baseline=[run(fired=False)]))
        self.assertIs(Verdict.REVIEW, j.verdict)
        self.assertIn("baseline도 1/1", j.reason)

    def test_failing_baseline_keeps_pass(self):
        j = self.verdict(case(), result([run(), run(), run()], baseline=[run(False, fired=False)]))
        self.assertIs(Verdict.PASS, j.verdict)

    def test_baseline_ignored_when_skill_must_not_fire(self):
        runs = [run(fired=False), run(fired=False), run(fired=False)]
        j = self.verdict(case(), result(runs, baseline=[run(fired=False)]))
        self.assertIs(Verdict.PASS, j.verdict)
        self.assertIn("미발동", j.reason)

    def test_soft_caps_without_values_never_review(self):
        j = self.verdict(case(), result([run(turns=999, tokens=10**9)] * 3))
        self.assertIs(Verdict.PASS, j.verdict)

    def test_soft_max_turns_exceeded_is_review(self):
        j = self.verdict(case(soft_max_turns=20), result([run(turns=30)] * 3))
        self.assertIs(Verdict.REVIEW, j.verdict)
        self.assertIn("평균 턴 30 > 상한 20", j.reason)

    def test_soft_max_tokens_exceeded_is_review(self):
        j = self.verdict(case(soft_max_tokens=500), result([run(tokens=800)] * 3))
        self.assertIs(Verdict.REVIEW, j.verdict)

    def test_unknown_cost_does_not_trip_soft_caps(self):
        runs = [RunResult(True, skill_fired=True, cost=None)] * 3
        self.assertIs(Verdict.PASS, self.verdict(case(soft_max_turns=1), result(runs)).verdict)

    def test_llm_grader_is_review_with_summary(self):
        j = self.verdict(case(grader="llm"), result([run()] * 3), llm_summary="LLM 2/3 통과(미통과 #5)")
        self.assertIs(Verdict.REVIEW, j.verdict)
        self.assertEqual("LLM 2/3 통과(미통과 #5)", j.reason)

    def test_llm_grader_never_fails_a_structurally_passing_case(self):
        j = self.verdict(case(grader="llm"), result([run()] * 3), llm_summary="LLM 0/3 통과")
        self.assertEqual((Verdict.REVIEW, "LLM 0/3 통과"), (j.verdict, j.reason))

    def test_structural_failure_still_fails_llm_case(self):
        j = self.verdict(case(grader="llm"), result([run(False)] * 3), llm_summary="무관")
        self.assertIs(Verdict.FAIL, j.verdict)


if __name__ == "__main__":
    unittest.main()
