"""수집·캡처·대조 스크립트의 판정 함수가 맞게 가르는지 확인한다."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import capture_helper
import collect_candidates
import probe_access
import tsv_io
import verify_quotes

HERE = Path(__file__).resolve().parent

SEARCH_PAGE = """
<li><a href="https://cafe.naver.com/somecafe/123?art=abc" class="title_link">간수치 재검 후기 새 창 열림</a>
<a href="https://cafe.naver.com/somecafe/123?art=abc" class="dsc_link">한 달 금주하고 다시 피검사를 받았더니 수치가 내려갔어요</a>
<a href="https://cafe.naver.com/somecafe">카페 이름</a></li>
<li><a href="https://cafe.naver.com/other/456"><b>콜레스테롤</b> 3개월 재검</a>
<a href="https://cafe.naver.com/other/456"><b>콜레스테롤</b> 3개월 재검</a></li>
<a href="https://ad.example.com/x">광고 링크 문구입니다</a>
"""


class ExtractTests(unittest.TestCase):
    def setUp(self):
        preset = collect_candidates.PRESETS["naver_cafe"]
        self.items = collect_candidates.extract(SEARCH_PAGE, preset["link_pattern"], preset["drop_text"])

    def test_groups_links_by_post_and_drops_query_and_other_links(self):
        self.assertEqual([i["url"] for i in self.items],
                         ["https://cafe.naver.com/somecafe/123", "https://cafe.naver.com/other/456"])

    def test_keeps_texts_longest_first_without_suffix_or_duplicates(self):
        self.assertEqual(self.items[0]["texts"][0], "한 달 금주하고 다시 피검사를 받았더니 수치가 내려갔어요")
        self.assertEqual(self.items[0]["texts"][1], "간수치 재검 후기")
        self.assertEqual(self.items[1]["texts"], ["콜레스테롤 3개월 재검"])

    def test_answer_links_fold_into_question(self):
        page = ('<a href="https://kin.naver.com/qna/detail.naver?dirId=7&amp;docId=9&amp;qb=x">질문 제목입니다</a>'
                '<a href="https://kin.naver.com/qna/detail.naver?answerNo=1&amp;dirId=7&amp;docId=9#answer1">답변 첫 줄입니다</a>')
        preset = collect_candidates.PRESETS["naver_kin"]
        items = collect_candidates.extract(page, preset["link_pattern"], preset["drop_text"], preset["canonical"])
        self.assertEqual([i["url"] for i in items], ["https://kin.naver.com/qna/detail.naver?dirId=7&docId=9"])
        self.assertEqual(len(items[0]["texts"]), 2)

    def test_from_html_reports_zero_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            pages = Path(tmp) / "pages"
            pages.mkdir()
            (pages / "01.html").write_text(SEARCH_PAGE, encoding="utf-8")
            (pages / "02.html").write_text("<p>로그인이 필요합니다</p>", encoding="utf-8")
            (pages / "03.html").write_text('<a href="https://cafe.naver.com/other/456">콜레스테롤 재검 다시</a>', encoding="utf-8")
            result = subprocess.run([sys.executable, str(HERE / "collect_candidates.py"), "--from-html", str(pages),
                                     "--source", "naver_cafe", "--group", "Q1", "--out", tmp], capture_output=True, text=True, check=True)
            lines = (Path(tmp) / "candidates.tsv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 3)
        self.assertTrue(all(line.split("\t")[0] == "Q1" for line in lines[1:]))
        self.assertEqual([line.split("\t")[1] for line in lines[1:]], ["01", "01|03"])
        self.assertIn("02.html naver_cafe 02: 링크 0건, 새 후보 0건 ← 0건", result.stdout)


class TsvTests(unittest.TestCase):
    def test_quote_at_cell_start_does_not_merge_rows_and_bom_is_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "list.tsv"
            path.write_text('\ufeffid\turl\ttitle\nP1\thttps://a\t"따옴표로 시작\nP2\thttps://b\t보통 제목\n', encoding="utf-8")
            rows = tsv_io.read_tsv(path)
        self.assertEqual([r["id"] for r in rows], ["P1", "P2"])

    def test_same_post_in_two_questions_keeps_both_groups(self):
        row = ["Q1", "검색어 하나", "naver_cafe", "https://a", "", "01.html"]
        collect_candidates.merge(row, "Q2", "검색어 둘")
        collect_candidates.merge(row, "Q1", "검색어 하나")
        self.assertEqual(row[:2], ["Q1|Q2", "검색어 하나|검색어 둘"])


class PickWindowTests(unittest.TestCase):
    WINDOWS = [
        {"owner": "Claude", "layer": 0, "id": 1, "w": 3000, "h": 2000},
        {"owner": "Google Chrome", "layer": 0, "id": 2, "w": 800, "h": 600},
        {"owner": "Google Chrome", "layer": 0, "id": 3, "w": 1400, "h": 900},
        {"owner": "Google Chrome", "layer": 25, "id": 4, "w": 4000, "h": 4000},
    ]

    def test_picks_largest_normal_window_of_owner(self):
        self.assertEqual(capture_helper.pick_window(self.WINDOWS, "Google Chrome"), 3)

    def test_none_when_owner_has_no_window(self):
        self.assertIsNone(capture_helper.pick_window(self.WINDOWS, "Safari"))

    def test_resume_skips_logged_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "capture_log.tsv"
            self.assertEqual(capture_helper.load_done(log), set())
            with log.open("a", encoding="utf-8") as f:
                f.write("P01\thttps://a\tP01_1.png\tsaved\n")
            self.assertEqual(capture_helper.load_done(log), {"P01"})
            with log.open("a", encoding="utf-8") as f:
                f.write("P02\thttps://b\tP02_1.png\tpartial\n")
            self.assertEqual(capture_helper.load_done(log), {"P01"})

    def test_next_shot_number_continues_after_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.assertEqual(capture_helper.next_shot_number(out, "P01"), 1)
            for name in ("P01_1.png", "P01_2.png", "P010_7.png"):
                (out / name).write_bytes(b"")
            self.assertEqual(capture_helper.next_shot_number(out, "P01"), 3)


class VerifyTests(unittest.TestCase):
    def run_verify(self, quotes, source="post.txt", write=True):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            if write:
                (base / "post.txt").write_text("의사가 “금주하고 한달 뒤 채혈을 해봅시다” 라고 했다.", encoding="utf-8")
            cases = [{"id": "P01", "source": source, "quotes": quotes, "evidence": "원문 저장"}]
            return [r[2] for r in verify_quotes.verify(cases, base)]

    def test_matches_despite_spacing_and_quote_marks(self):
        self.assertEqual(self.run_verify(['"금주하고 한 달 뒤 채혈을']), ["일치"])
        self.assertEqual(self.run_verify(["금주하고한달뒤 채혈을 해봅시다"]), ["일치"])

    def test_altered_quote_is_mismatch(self):
        self.assertEqual(self.run_verify(["금주하고 두달 뒤 채혈을"]), ["불일치"])

    def test_missing_source_is_reported(self):
        self.assertEqual(self.run_verify(["아무 말이나 적은 인용"], write=False), ["원문 없음"])

    def test_empty_or_tiny_quotes_are_not_matches(self):
        self.assertEqual(self.run_verify([""]), ["너무 짧음"])
        self.assertEqual(self.run_verify([]), ["인용 없음"])

    def test_case_without_quotes_list_fails(self):
        with self.assertRaises(ValueError):
            verify_quotes.verify([{"id": "P01", "source": "x", "quotes": "문자열"}], Path("."))

    def test_cli_exit_code_and_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "a.txt").write_text("수치가 그대로였다", encoding="utf-8")
            cases = [{"id": "P01", "source": "a.txt", "quotes": ["수치가 그대로"], "evidence": "스크린샷 판독"},
                     {"id": "P02", "source": "a.txt", "quotes": ["수치가 내려갔다"], "evidence": "원문 저장"}]
            (base / "cases.json").write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
            script = str(HERE / "verify_quotes.py")
            failed = subprocess.run([sys.executable, script, str(base / "cases.json")], capture_output=True, text=True)
            sample = subprocess.run([sys.executable, script, str(base / "cases.json"), "--sample", "5"],
                                    capture_output=True, text=True, check=True)
        self.assertEqual(failed.returncode, 1)
        self.assertIn("P02 #1 불일치", failed.stdout)
        self.assertIn("P01", sample.stdout)
        self.assertNotIn("P02", sample.stdout)


class ClassifyTests(unittest.TestCase):
    def test_short_login_page_is_suspected_block(self):
        self.assertEqual(probe_access.classify("200", "<p>로그인이 필요합니다</p>"), "로그인·차단 화면 의심")

    def test_long_page_is_body(self):
        self.assertEqual(probe_access.classify("200", "<p>" + "본문 글자 " * 400 + "로그인</p>"), "본문 있음")

    def test_redirect_to_login_is_suspected_block(self):
        page = "<p>" + "본문 글자 " * 400 + "</p>"
        self.assertEqual(probe_access.classify("200", page, "https://nid.example.com/nidlogin.login"), "로그인·차단 화면 의심")

    def test_non_200_is_failure(self):
        self.assertEqual(probe_access.classify("403", "x" * 5000), "받기 실패")


if __name__ == "__main__":
    unittest.main()
