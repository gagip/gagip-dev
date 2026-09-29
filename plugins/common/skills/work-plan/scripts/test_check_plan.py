"""check_plan.py 단위 테스트.  python3 test_check_plan.py"""

import unittest

from check_plan import check

PROBLEM = """## 3. 판정 기준 (OKR)

| Objective | KR | 판정 기준 | 판정 방법 | 판정 시점 | 유형 |
|---|---|---|---|---|---|
| O1.1 | KR1 | 실패 경로마다 안내 문구가 표시된다 | 확인 | 구현 후 | 약속 |
| O1.2 | KR1 | 안내 문구가 동사로 시작한다 | 에이전트 채점 | 구현 후 | 약속 |
"""

DESIGN = """## 1. 요구사항

| # | 결정 | 이유 | KR |
|---|---|---|---|
| D1 | 실패 코드를 `LoginError` 하나로 모은다 | 분기를 한 곳에서 문구로 바꾼다 | O1.1 KR1 |
| D2 | 문구는 문자열 리소스에 둔다 | 번역 흐름을 그대로 쓴다 | O1.2 KR1 |
| D3 | 실패 로그를 서버로 보낸다 | 재발을 추적한다 | O1.1 KR1 |
"""

GOOD = """# 로그인 실패 안내 플랜

- 작성: 2026-09-30
- 문제 정의: docs/problem.md
- 설계: docs/design.md
- 브랜치: feat/login-failure-message
- 기한: 10/02(금) 베타 행사
- 상태: 초안

## 1. 작업 범위

- 이번에 하는 것: D1, D2

### 미루는 작업

| 작업 | 이유 |
|---|---|
| D3 실패 로그 전송 | 서버 수집 엔드포인트가 아직 없다 |

## 2. 작업 설계

### 실패 안내

- [ ] 에이전트: 실패 경로 목록을 docs/failures.md에 저장한다 [D1]
- [ ] 에이전트: `LoginError`로 실패 코드를 모은다 ← 실패 경로 목록 저장 [D1]
- [ ] 사람(결정): 안내 문구 초안 중 하나를 고른다 ← 실패 경로 목록 저장 [D2]
- [ ] 사람(리뷰): 실패 경로마다 문구가 뜨는지 보고 승인하거나 반려한다 ← `LoginError` [O1.1 KR1]
- [ ] 에이전트: 문구가 동사로 시작하는지 채점한다 [O1.2 KR1]
- [ ] 에이전트: 브랜치를 만든다 [공통]

## 3. 검증 방법

| 대상 | 확인 방법 | 예상되는 관찰 | 그때의 해석 |
|---|---|---|---|
| O1.1 KR1 | 실패 경로마다 에뮬레이터로 실패를 일으킨다 | 문구가 뜬다 | 성립 |
| O1.2 KR1 | 에이전트 채점 | 모두 동사로 시작 | 성립 |

## 4. 리스크

| 리스크 | 대응 |
|---|---|
| SDK가 취소를 실패로 보고 | 취소 코드를 따로 거른다 |

## 5. 일정과 기한 판정

| 날짜 | 고정 일정 | 사람 몫 (크기) | 메모 |
|---|---|---|---|
| 10/01(목) | — | 문구 고르기 (짧음) | |

| 목표 | 기한 안에 들어가는가 | 근거 | 들어가지 않으면 |
|---|---|---|---|
| O1 | 들어감 | 사람 몫 짧음 둘 | — |

## 6. 사용자가 정할 것

1. 없음
"""


def errs(doc, design=DESIGN, problem=PROBLEM):
    return check(doc, design, problem)[0]


class CheckPlanTest(unittest.TestCase):
    def test_clean_document_has_no_findings(self):
        errors, warnings = check(GOOD, DESIGN, PROBLEM)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_missing_design_header_is_error(self):
        self.assertTrue(any("`- 설계:`" in e for e in errs(GOOD.replace("- 설계: docs/design.md\n", ""))))

    def test_bad_status_is_error(self):
        self.assertTrue(any("상태" in e for e in errs(GOOD.replace("상태: 초안", "상태: 진행 중"))))
        self.assertEqual(errs(GOOD.replace("상태: 초안", "상태: 승인됨 (2026-09-30)")), [])

    def test_unlabeled_task_is_error(self):
        doc = GOOD.replace("- [ ] 에이전트: 브랜치를 만든다", "- [ ] 브랜치를 만든다")
        self.assertTrue(any("담당 표시 없음" in e for e in errs(doc)))

    def test_dated_agent_task_is_error(self):
        doc = GOOD.replace("에이전트: 브랜치를 만든다", "에이전트: 10/01에 브랜치를 만든다")
        self.assertTrue(any("날짜" in e for e in errs(doc)))

    def test_missing_trace_is_error(self):
        doc = GOOD.replace("브랜치를 만든다 [공통]", "브랜치를 만든다")
        self.assertTrue(any("대응 대상이 없음" in e for e in errs(doc)))

    def test_unknown_decision_is_error(self):
        doc = GOOD.replace("하나를 고른다 ← 실패 경로 목록 저장 [D2]", "하나를 고른다 ← 실패 경로 목록 저장 [D9]")
        self.assertTrue(any("설계에 없는 D9" in e for e in errs(doc)))

    def test_unknown_kr_is_error(self):
        doc = GOOD.replace("채점한다 [O1.2 KR1]", "채점한다 [O7.1 KR1]")
        self.assertTrue(any("문제 정의에 없는 O7.1 KR1" in e for e in errs(doc)))

    def test_uncovered_decision_is_error(self):
        doc = GOOD.replace("하나를 고른다 ← 실패 경로 목록 저장 [D2]", "하나를 고른다 ← 실패 경로 목록 저장 [O1.2 KR1]")
        self.assertTrue(any("D2를 이루는 작업이 없음" in e for e in errs(doc)))

    def test_deferred_decision_needs_no_task(self):
        self.assertFalse(any("D3" in e for e in errs(GOOD)))
        doc = GOOD.replace("| D3 실패 로그 전송 |", "| 실패 로그 전송 |")
        self.assertTrue(any("D3를 이루는 작업이 없음" in e for e in errs(doc)))

    def test_kr_without_verification_is_error(self):
        doc = GOOD.replace("| O1.2 KR1 | 에이전트 채점 |", "| 문구 | 에이전트 채점 |")
        self.assertTrue(any("O1.2 KR1의 검증 방법" in e for e in errs(doc)))

    def test_deadline_without_schedule_is_error(self):
        doc = GOOD.split("## 5. 일정과 기한 판정")[0] + "## 6. 사용자가 정할 것\n\n1. 없음\n"
        self.assertTrue(any("기한 판정 절이 없음" in e for e in errs(doc)))

    def test_no_deadline_with_schedule_warns(self):
        errors, warnings = check(GOOD.replace("기한: 10/02(금) 베타 행사", "기한: 없음"), DESIGN, PROBLEM)
        self.assertEqual(errors, [])
        self.assertTrue(any("일정 절" in w for w in warnings))

    def test_review_without_end_condition_warns(self):
        doc = GOOD.replace("보고 승인하거나 반려한다", "본다")
        self.assertTrue(any("리뷰 항목" in w for w in check(doc, DESIGN, PROBLEM)[1]))

    def test_collect_without_count_warns(self):
        doc = GOOD.replace("에이전트: 브랜치를 만든다", "에이전트: 사례를 수집한다")
        self.assertTrue(any("수집 항목" in w for w in check(doc, DESIGN, PROBLEM)[1]))
        doc = GOOD.replace("에이전트: 브랜치를 만든다", "에이전트: 사례를 5건 수집한다")
        self.assertFalse(any("수집 항목" in w for w in check(doc, DESIGN, PROBLEM)[1]))

    def test_foreign_sections_are_errors(self):
        for heading in ["## 배경", "## 1. 문제 정의", "## 목표 트리", "## 판정 기준 (OKR)", "## 요구사항",
                        "## 제약", "## 기술 리스크 / 선행 검증", "## 미해결 설계 사안"]:
            self.assertTrue(any("오지 않는 절" in e for e in errs(GOOD + f"\n{heading}\n")), heading)

    def test_plain_risk_section_is_fine(self):
        self.assertFalse(any("오지 않는 절" in e for e in errs(GOOD)))

    def test_no_tasks_is_error(self):
        doc = "\n".join(l for l in GOOD.splitlines() if not l.startswith("- [ ]"))
        self.assertTrue(any("작업 항목을 찾지 못함" in e for e in check(doc)[0]))

    def test_cross_checks_skipped_without_other_docs(self):
        self.assertEqual(check(GOOD.replace("[D2]", "[D9]"))[0], [])


if __name__ == "__main__":
    unittest.main()
