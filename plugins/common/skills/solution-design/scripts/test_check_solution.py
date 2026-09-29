"""check_solution.py 단위 테스트.  python3 test_check_solution.py"""

import unittest

from check_solution import check

PROBLEM = """## 3. 판정 기준 (OKR)

| Objective | KR | 판정 기준 | 판정 방법 | 판정 시점 | 유형 |
|---|---|---|---|---|---|
| O1.1 | KR1 | 실패 경로마다 안내 문구가 표시된다 | 확인 | 구현 후 | 약속 |
| O1.2 | KR1 | 안내 문구가 동사로 시작한다 | 에이전트 채점 | 구현 후 | 약속 |
"""

GOOD = """# 로그인 실패 안내 설계

- 작성: 2026-09-30
- 문제 정의: docs/problem.md
- 상태: 초안

## 1. 요구사항

### 1-1. 구조

| # | 결정 | 이유 | KR |
|---|---|---|---|
| D1 | 실패 코드를 `LoginError` 하나로 모은다 | 화면마다 흩어진 분기를 한 곳에서 문구로 바꿀 수 있다 | O1.1 KR1 |
| D2 | 문구는 문자열 리소스에 둔다 | 번역·검수 흐름을 그대로 쓴다 | O1.2 KR1 |

## 2. 제약

- **서버 코드 변경 불가** — 클라이언트에서 코드만 해석한다

## 3. 기술 리스크 / 선행 검증

- **검증할 질문**: 소셜 SDK가 취소와 실패를 구분해 주는가

## 4. 미해결 설계 사안

- 없음
"""


class CheckSolutionTest(unittest.TestCase):
    def test_clean_document_has_no_findings(self):
        errors, warnings = check(GOOD, PROBLEM)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_missing_problem_header_is_error(self):
        errors, _ = check(GOOD.replace("- 문제 정의: docs/problem.md\n", ""))
        self.assertTrue(any("문제 정의:" in e for e in errors))

    def test_empty_reason_is_error(self):
        errors, _ = check(GOOD.replace("번역·검수 흐름을 그대로 쓴다", "—"))
        self.assertTrue(any("D2의 이유" in e for e in errors))

    def test_bad_kr_cell_is_error(self):
        errors, _ = check(GOOD.replace("| O1.2 KR1 |", "| 전반 |"))
        self.assertTrue(any("D2의 KR 칸" in e for e in errors))

    def test_dash_kr_allowed_only_when_problem_skipped(self):
        doc = GOOD.replace("| O1.2 KR1 |", "| — |")
        errors, _ = check(doc)
        self.assertTrue(any("D2의 KR 칸" in e for e in errors))
        errors, _ = check(doc.replace("docs/problem.md", "생략 (한 줄 수정)"))
        self.assertFalse(any("D2의 KR 칸" in e for e in errors))

    def test_unknown_kr_is_error_with_problem(self):
        errors, _ = check(GOOD.replace("| O1.2 KR1 |", "| O9.9 KR1 |"), PROBLEM)
        self.assertTrue(any("O9.9 KR1" in e for e in errors))

    def test_uncovered_kr_warns(self):
        _, warnings = check(GOOD.replace("| O1.2 KR1 |", "| O1.1 KR1 |"), PROBLEM)
        self.assertTrue(any("O1.2 KR1" in w for w in warnings))

    def test_duplicate_decision_is_error(self):
        errors, _ = check(GOOD.replace("| D2 |", "| D1 |"))
        self.assertTrue(any("두 번" in e for e in errors))

    def test_foreign_sections_are_errors(self):
        for heading in ["## 배경", "## 2. 목표 / 비목표", "## 5. 성공 지표 / 검증 방법", "## 작업 설계",
                        "## 5. 리스크 / 오픈 이슈", "## 코드 리뷰", "## 일정"]:
            errors, _ = check(GOOD + f"\n{heading}\n")
            self.assertTrue(any("오지 않는 절" in e for e in errors), heading)

    def test_technical_risk_section_is_fine(self):
        errors, _ = check(GOOD)
        self.assertFalse(any("오지 않는 절" in e for e in errors))

    def test_task_checkbox_is_error(self):
        errors, _ = check(GOOD + "- [ ] 에이전트: 구현한다\n")
        self.assertTrue(any("작업 체크박스" in e for e in errors))

    def test_missing_decision_table_is_error(self):
        errors, _ = check("# 설계\n\n- 문제 정의: 생략 (테스트)\n")
        self.assertTrue(any("결정 표" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
