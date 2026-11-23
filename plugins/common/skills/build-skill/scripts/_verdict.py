"""케이스 결과를 PASS / FAIL / REVIEW로 판정한다. 같은 결과에는 늘 같은 판정이 나온다."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from _harness import Case, CaseResult, RunResult


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


@dataclass(frozen=True)
class Judgement:
    verdict: Verdict
    reason: str   # 판정 근거 한 줄


def _rate(runs: list[RunResult]) -> float:
    return sum(r.passed for r in runs) / len(runs) if runs else 0.0


def _mean(values: list[int]) -> float | None:
    return sum(values) / len(values) if values else None


# 결정: 판정은 위에서부터 처음 맞는 규칙 하나로 정한다. 종료 코드를 바꾸는 것은 FAIL뿐이고, REVIEW는
#   "통과는 했지만 사람이 볼 이유가 있다"는 표시다. 통과/실패 두 값만 두면 baseline과 차이가 없는 스킬이나
#   의미를 코드로 잴 수 없는 산출물이 PASS로 묻힌다.
# 결정: 실행 오류(scaffold 실패·시간 초과·인증 실패·check 예외)는 ERROR 상태를 따로 두지 않고 FAIL로 묶는다.
#   상태를 넷으로 늘리면 release_check·CI가 읽는 종료 코드 규칙도 함께 바뀌어야 한다.
# 결정: LLM 채점(GRADER="llm")은 불합격이어도 REVIEW까지만 낸다. 사람 판정과의 일치도가 확인되지 않은
#   채점기가 릴리스를 막게 하지 않는다. LLM 결과는 근거로만 보여 주고 최종 결정은 사람이 한다.
def judge(case: Case, result: CaseResult, threshold: float, *, llm_summary: str | None = None) -> Judgement:
    """케이스 하나를 판정한다.

    llm_summary는 GRADER="llm" 케이스의 채점 요약 한 줄이다(채점을 껐거나 못 했으면 그 사유).
    """
    assert 0.0 <= threshold <= 1.0, f"임계값은 0~1이어야 한다: {threshold}"
    runs = result.runs
    total = len(runs)
    passed = sum(r.passed for r in runs)

    errors = [r for r in runs if r.error]
    if errors:
        return Judgement(Verdict.FAIL, f"실행 오류 {len(errors)}/{total}: {errors[0].reason}")
    if not runs or _rate(runs) < threshold:
        return Judgement(Verdict.FAIL, f"통과 {passed}/{total} < 임계 {threshold:g}")
    if passed < total:
        return Judgement(Verdict.REVIEW, f"통과 {passed}/{total}, 임계 {threshold:g} 충족")

    # baseline은 스킬이 실제로 발동한 케이스에서만 본다. "발동하지 않아야 통과"하는 케이스는
    # 스킬을 뺀 baseline이 언제나 통과하므로 비교가 뜻이 없다.
    fired = any(r.skill_fired for r in runs)
    if result.baseline and fired and _rate(result.baseline) >= _rate(runs):
        base_pass = sum(r.passed for r in result.baseline)
        return Judgement(Verdict.REVIEW,
                         f"baseline도 {base_pass}/{len(result.baseline)} 통과: 스킬 기여 불명")

    costs = [r.cost for r in runs if r.cost is not None]
    mean_turns = _mean([c.turns for c in costs])
    if case.soft_max_turns is not None and mean_turns is not None and mean_turns > case.soft_max_turns:
        return Judgement(Verdict.REVIEW, f"평균 턴 {mean_turns:.0f} > 상한 {case.soft_max_turns}")
    mean_tokens = _mean([c.tokens for c in costs])
    if case.soft_max_tokens is not None and mean_tokens is not None and mean_tokens > case.soft_max_tokens:
        return Judgement(Verdict.REVIEW, f"평균 토큰 {mean_tokens:.0f} > 상한 {case.soft_max_tokens}")

    if case.grader == "llm":
        return Judgement(Verdict.REVIEW, llm_summary or "LLM 채점 결과 없음")

    if result.baseline and not fired:
        return Judgement(Verdict.PASS, f"통과 {passed}/{total} (미발동 케이스라 baseline 비교 안 함)")
    if not result.baseline:
        return Judgement(Verdict.PASS, f"통과 {passed}/{total} (baseline 미실행)")
    return Judgement(Verdict.PASS, f"통과 {passed}/{total}")
