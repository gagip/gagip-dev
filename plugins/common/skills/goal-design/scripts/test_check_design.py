"""check_design.py 단위 테스트.  python3 test_check_design.py"""

import unittest

from check_design import check

GOOD = """# 설계

## 2. 목표 트리

O1. 로그인 실패가 안내된다
 ├ O1.1 실패 경로가 목록으로 있다

## 3. 판정 기준 (OKR)

| Objective | KR | 판정 기준 | 판정 방법 | 판정 시점 | 유형 |
|---|---|---|---|---|---|
| O1.1 | KR1 | 실패 경로 목록이 문서에 있다 | 확인 | 화요일 | 약속 |

## 4. 작업 설계

- [ ] 에이전트: 실패 경로를 조사해 목록으로 저장
- [ ] 사람(리뷰): 목록을 승인하거나 반려한다 ← O1.1
"""


class CheckDesignTest(unittest.TestCase):
    def test_clean_document_has_no_findings(self):
        errors, warnings = check(GOOD)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_task_without_label_is_error(self):
        errors, _ = check(GOOD + "- [ ] 문구를 정리한다\n")
        self.assertTrue(any("담당 표시 없음" in e for e in errors))

    def test_dated_agent_task_is_error(self):
        errors, _ = check(GOOD + "- [ ] 에이전트: 9/30에 빌드한다\n")
        self.assertTrue(any("날짜" in e for e in errors))

    def test_reference_to_undefined_id_is_error(self):
        errors, _ = check(GOOD + "- [ ] 에이전트: 빌드한다 ← O9.9\n")
        self.assertTrue(any("O9.9" in e for e in errors))

    def test_bad_method_and_kind_are_errors(self):
        doc = GOOD.replace("| 확인 | 화요일 | 약속 |", "| 눈으로 | 화요일 | 필수 |")
        errors, _ = check(doc)
        self.assertTrue(any("판정 방법" in e for e in errors))
        self.assertTrue(any("유형" in e for e in errors))

    def test_numeric_kr_without_candidate_mark_warns(self):
        doc = GOOD.replace("실패 경로 목록이 문서에 있다", "사용자 60% 이상이 안내를 본다")
        _, warnings = check(doc)
        self.assertTrue(any("수치" in w for w in warnings))
        _, warnings = check(doc.replace("사용자 60%", "후보: 사용자 60%"))
        self.assertFalse(any("수치" in w for w in warnings))

    def test_review_without_end_condition_warns(self):
        _, warnings = check(GOOD + "- [ ] 사람(리뷰): 동료 코드 리뷰\n")
        self.assertTrue(any("리뷰 항목" in w for w in warnings))

    def test_collect_without_count_warns_but_investigation_does_not(self):
        _, warnings = check(GOOD + "- [ ] 에이전트: 설문 응답을 모은다\n")
        self.assertTrue(any("수집 항목" in w for w in warnings))
        _, warnings = check(GOOD + "- [ ] 에이전트: 이벤트가 수집되는지 조사해 목록으로 저장\n")
        self.assertFalse(any("수집 항목" in w for w in warnings))

    def test_task_referencing_its_own_section_is_error(self):
        doc = GOOD + "\n### O1.1\n\n- [ ] 에이전트: 근거를 정리한다 ← O1.1\n"
        errors, _ = check(doc)
        self.assertTrue(any("자기가 속한 O1.1" in e for e in errors))

    def test_named_task_in_own_section_is_fine(self):
        doc = GOOD + "\n### O1.1\n\n- [ ] 사람(리뷰): 구현을 승인하거나 반려한다 ← O1.1 구현\n"
        errors, _ = check(doc)
        self.assertFalse(any("자기가 속한" in e for e in errors))

    def test_referencing_other_section_is_fine(self):
        doc = GOOD.replace(" ├ O1.1", " ├ O1.1 실패 경로가 목록으로 있다\n ├ O1.2") + "\n### O1.2\n\n- [ ] 에이전트: 안내를 구현한다 ← O1.1\n"
        errors, _ = check(doc)
        self.assertFalse(any("자기가 속한" in e for e in errors))

    def test_count_of_drafts_warns_without_candidate_mark(self):
        doc = GOOD.replace("실패 경로 목록이 문서에 있다", "초안 2안이 빈칸 없이 있다")
        _, warnings = check(doc)
        self.assertTrue(any("수치" in w for w in warnings))

    def test_missing_kr_table_is_error(self):
        errors, _ = check("# 설계\n\n- [ ] 에이전트: 조사한다\n")
        self.assertTrue(any("KR 표" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
