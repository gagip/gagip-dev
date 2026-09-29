"""check_problem.py 단위 테스트.  python3 test_check_problem.py"""

import unittest

from check_problem import check

GOOD = """# 로그인 문제 정의

## 1. 문제 정의

### O1. 로그인 실패를 사용자가 이해한다

| 칸 | 내용 |
|---|---|
| 지금 상태 | 실패하면 아무 안내가 없다 |
| 이룰 상태 | 실패하면 사용자가 이유를 안다 |
| 왜 | 문의 급증 (원천: 회의록) |
| 범위 밖 | 가입 실패 |

## 2. 목표 트리

O1. 로그인 실패를 사용자가 이해한다
 ├ O1.1 실패 이유가 사용자에게 전달된다

## 3. 판정 기준 (OKR)

| Objective | KR | 판정 기준 | 판정 방법 | 판정 시점 | 유형 |
|---|---|---|---|---|---|
| O1.1 | KR1 | 실패 경로마다 안내 문구가 표시된다 | 확인 | 구현 후 | 약속 |

## 4. 사용자가 정할 것

1. 소셜 로그인도 포함하나?
"""


class CheckProblemTest(unittest.TestCase):
    def test_clean_document_has_no_findings(self):
        errors, warnings = check(GOOD)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_bad_method_and_kind_are_errors(self):
        doc = GOOD.replace("| 확인 | 구현 후 | 약속 |", "| 눈으로 | 구현 후 | 필수 |")
        errors, _ = check(doc)
        self.assertTrue(any("판정 방법" in e for e in errors))
        self.assertTrue(any("유형" in e for e in errors))

    def test_empty_when_is_error(self):
        errors, _ = check(GOOD.replace("| 확인 | 구현 후 |", "| 확인 | — |"))
        self.assertTrue(any("판정 시점" in e for e in errors))

    def test_numeric_kr_without_candidate_mark_warns(self):
        doc = GOOD.replace("실패 경로마다 안내 문구가 표시된다", "사용자 60% 이상이 안내를 본다")
        _, warnings = check(doc)
        self.assertTrue(any("수치" in w for w in warnings))
        _, warnings = check(doc.replace("사용자 60%", "후보: 사용자 60%"))
        self.assertFalse(any("수치" in w for w in warnings))

    def test_count_of_drafts_warns_without_candidate_mark(self):
        doc = GOOD.replace("실패 경로마다 안내 문구가 표시된다", "초안 2안이 빈칸 없이 있다")
        _, warnings = check(doc)
        self.assertTrue(any("수치" in w for w in warnings))

    def test_undefined_objective_is_error(self):
        errors, _ = check(GOOD.replace("| O1.1 | KR1 |", "| O9.9 | KR1 |"))
        self.assertTrue(any("O9.9" in e for e in errors))

    def test_duplicate_kr_is_error(self):
        row = "| O1.1 | KR1 | 실패 경로마다 안내 문구가 표시된다 | 확인 | 구현 후 | 약속 |\n"
        errors, _ = check(GOOD.replace(row, row + row))
        self.assertTrue(any("두 번" in e for e in errors))

    def test_task_checkbox_is_error(self):
        errors, _ = check(GOOD + "- [ ] 에이전트: 실패 경로를 조사한다\n")
        self.assertTrue(any("작업 체크박스" in e for e in errors))

    def test_foreign_sections_are_errors(self):
        for heading in ["## 5. 작업 설계", "## 6. 일정과 기한 판정", "## 7. 위험", "## 요구사항"]:
            errors, _ = check(GOOD + f"\n{heading}\n")
            self.assertTrue(any("오지 않는 절" in e for e in errors), heading)

    def test_objective_heading_with_foreign_word_is_fine(self):
        doc = GOOD.replace("### O1. 로그인 실패를 사용자가 이해한다", "### O1. 작업 시간이 줄어든다")
        errors, _ = check(doc)
        self.assertFalse(any("오지 않는 절" in e for e in errors))

    def test_missing_kr_table_is_error(self):
        errors, _ = check("# 문제 정의\n\nO1. 무언가\n")
        self.assertTrue(any("KR 표" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
