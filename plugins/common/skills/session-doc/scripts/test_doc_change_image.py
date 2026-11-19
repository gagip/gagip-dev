import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import doc_change_image as dci  # noqa: E402

BASE = """# 계획
## 범위
첫 줄은 그대로 둔다.
버튼 이름은 다시 재기로 한다.

| 화면 | 문구 |
|---|---|
| 첫 화면 | 시작하기 |
"""


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPTS / "doc_change_image.py"), *map(str, args)],
                          capture_output=True, text=True)


class DiffRows(unittest.TestCase):
    def test_no_change_gives_no_rows(self):
        self.assertEqual(dci.diff_rows(BASE, BASE), [])

    def test_added_line_only(self):
        new = BASE.replace("첫 줄은 그대로 둔다.\n", "첫 줄은 그대로 둔다.\n새로 넣은 줄.\n")
        rows = dci.diff_rows(BASE, new)
        self.assertEqual(rows, [dci.Row(4, "범위", None, "새로 넣은 줄.")])
        page = dci.render_html(rows, "t", 1, 1)
        self.assertIn("(없음)</span></td><td><ins>새로 넣은 줄.</ins>", page)

    def test_deleted_line_only(self):
        new = BASE.replace("첫 줄은 그대로 둔다.\n", "")
        rows = dci.diff_rows(BASE, new)
        self.assertEqual(rows, [dci.Row(3, "범위", "첫 줄은 그대로 둔다.", None)])
        page = dci.render_html(rows, "t", 1, 1)
        self.assertIn("<del>첫 줄은 그대로 둔다.</del></td><td><span class=\"none\">(없음)", page)

    def test_table_row_edit_marks_only_changed_cell(self):
        new = BASE.replace("| 첫 화면 | 시작하기 |", "| 첫 화면 | 바로 시작 |")
        rows = dci.diff_rows(BASE, new)
        self.assertEqual([(r.line, r.section) for r in rows], [(8, "범위")])
        before, after = dci.word_diff(rows[0].old, rows[0].new)
        self.assertEqual(before, "| 첫 화면 | <del>시작하기</del> |")
        self.assertEqual(after, "| 첫 화면 | <ins>바로 시작</ins> |")

    def test_korean_word_level_diff(self):
        before, after = dci.word_diff("버튼 이름은 다시 재기로 한다.", "버튼 이름은 다시 측정으로 한다.")
        self.assertEqual(before, "버튼 이름은 다시 <del>재기로</del> 한다.")
        self.assertEqual(after, "버튼 이름은 다시 <ins>측정으로</ins> 한다.")

    def test_edit_next_to_inserted_line_pairs_similar_lines(self):
        new = BASE.replace("버튼 이름은 다시 재기로 한다.", "전혀 다른 새 문장이 들어간다.\n버튼 이름은 다시 측정으로 한다.")
        rows = dci.diff_rows(BASE, new)
        self.assertEqual([(r.old, r.new) for r in rows],
                         [(None, "전혀 다른 새 문장이 들어간다."),
                          ("버튼 이름은 다시 재기로 한다.", "버튼 이름은 다시 측정으로 한다.")])

    def test_table_rows_pair_with_their_own_edit_not_inserted_row(self):
        old = "## 절\n| 첫 화면 | 시작하기 |\n| 둘째 | 이동 |"
        new = "## 절\n| 새 행 | 추가 |\n| 첫 화면 | 바로 시작 |\n| 둘째 | 이동하기 |"
        self.assertEqual([(r.old, r.new) for r in dci.diff_rows(old, new)],
                         [(None, "| 새 행 | 추가 |"),
                          ("| 첫 화면 | 시작하기 |", "| 첫 화면 | 바로 시작 |"),
                          ("| 둘째 | 이동 |", "| 둘째 | 이동하기 |")])

    def test_line_numbers_ignore_form_feed(self):
        self.assertEqual(dci.diff_rows("a\n\x0c\nx\nb", "a\n\x0c\nx\nc")[0].line, 4)

    def test_heading_keeps_trailing_hash_in_word(self):
        self.assertEqual(dci.headings(["## C#"]), ["C#"])

    def test_blank_line_changes_are_skipped(self):
        self.assertEqual(dci.diff_rows(BASE, BASE.replace("\n\n", "\n\n\n")), [])

    def test_heading_inside_code_fence_is_ignored(self):
        self.assertEqual(dci.headings(["## 절", "```", "# 주석", "```", "본문"])[-1], "절")

    def test_html_escaped(self):
        before, after = dci.word_diff("<b> a", "<b> b")
        self.assertEqual(after, "&lt;b&gt; <ins>b</ins>")


class SplitPages(unittest.TestCase):
    def rows(self, section, n):
        return [dci.Row(i, section, None, "x") for i in range(n)]

    def test_twenty_rows_fit_one_image(self):
        self.assertEqual(len(dci.split_pages(self.rows("A", 20))), 1)

    def test_sections_are_not_cut_when_they_fit(self):
        pages = dci.split_pages(self.rows("A", 15) + self.rows("B", 10))
        self.assertEqual([len(p) for p in pages], [15, 10])

    def test_long_section_is_cut_at_limit(self):
        pages = dci.split_pages(self.rows("A", 45))
        self.assertEqual([len(p) for p in pages], [20, 20, 5])


class Cli(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.base = self.dir / "base.md"
        self.doc = self.dir / "doc.md"
        self.base.write_text(BASE, encoding="utf-8")

    def test_empty_change_writes_nothing(self):
        self.doc.write_text(BASE, encoding="utf-8")
        r = run(self.doc, "--base-file", self.base, "--out", self.dir / "o.png")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("바뀐 줄 없음", r.stdout)
        self.assertFalse((self.dir / "o.html").exists())

    def test_over_twenty_rows_reports_remaining_images(self):
        extra = "".join(f"## 절{k}\n" + "".join(f"줄 {k}-{i}\n" for i in range(12)) for k in range(3))
        self.doc.write_text(BASE + extra, encoding="utf-8")
        r = run(self.doc, "--base-file", self.base, "--out", self.dir / "o.png", "--html-only")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("나머지 2장", r.stdout)
        self.assertTrue((self.dir / "o_3.html").exists())

    def test_git_head_base(self):
        subprocess.run(["git", "init", "-q", str(self.dir)], check=True)
        subprocess.run(["git", "-C", str(self.dir), "add", "base.md"], check=True)
        subprocess.run(["git", "-C", str(self.dir), "-c", "user.email=e@e", "-c", "user.name=e",
                        "commit", "-qm", "init"], check=True)
        self.base.write_text(BASE.replace("재기로", "측정으로"), encoding="utf-8")
        r = run(self.base, "--out", self.dir / "o.png", "--html-only")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("<ins>측정으로</ins>", (self.dir / "o.html").read_text(encoding="utf-8"))

    def test_unknown_git_rev_fails(self):
        subprocess.run(["git", "init", "-q", str(self.dir)], check=True)
        r = run(self.base, "--base", "nope", "--out", self.dir / "o.png", "--html-only")
        self.assertEqual(r.returncode, 2)
        self.assertIn("git 시점이 없다", r.stderr)

    @unittest.skipUnless(dci.find_chrome(), "크롬 없음")
    def test_png_rendered_with_relative_out(self):
        self.doc.write_text(BASE.replace("재기로", "측정으로"), encoding="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPTS / "doc_change_image.py"), "doc.md",
                            "--base-file", "base.md", "--out", "o.png"], capture_output=True, text=True, cwd=self.dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.dir / "o.png").read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
