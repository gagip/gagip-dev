"""validate_html.py 단위 테스트.  python3 test_validate_html.py"""

import tempfile
import unittest
from pathlib import Path

from validate_html import validate

PAGE = """<!doctype html>
<html lang="ko">
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>표 검사</title>
<style>.wrap {{ overflow-x: auto; }} @media print {{ body {{ color: #000; }} }}</style>
</head>
<body>
<main>
<h1>표 검사</h1>
<a href="https://example.com/source">원문</a>
{tables}
<script id="brief-data" type="application/json">
{{"document": "표 검사", "mode": "report", "asOf": "2026-01-01", "audience": ["작성자"], "summary": "표 검사", "sources": {{}}}}
</script>
</main>
</body>
</html>
"""


class TableWidthTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def brief_with(self, tables):
        path = Path(self.directory.name) / "brief.html"
        path.write_text(PAGE.format(tables=tables), encoding="utf-8")
        return path

    def test_matching_widths_with_spans_have_no_warning(self):
        path = self.brief_with("""<table>
<thead>
<tr><th rowspan="2">항목</th><th colspan="2">값</th></tr>
<tr><th>전</th><th>후</th></tr>
</thead>
<tbody>
<tr><td colspan="3">묶음 제목</td></tr>
<tr><td rowspan="2">가</td><td>1</td><td>2</td></tr>
<tr><td>3</td><td>4</td></tr>
</tbody>
</table>""")

        errors, warnings = validate(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_rows_after_rowspan_ends_have_full_width(self):
        path = self.brief_with("""<table>
<thead><tr><th>항목</th><th>값</th><th>출처</th></tr></thead>
<tbody>
<tr><td rowspan="2">가</td><td>1</td><td>S1</td></tr>
<tr><td>2</td><td>S2</td></tr>
<tr><td>나</td><td>3</td><td>S3</td></tr>
</tbody>
</table>""")

        errors, warnings = validate(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_rowspan_stays_inside_its_row_group(self):
        path = self.brief_with("""<table>
<thead><tr><th rowspan="2">항목</th><th rowspan="0">값</th></tr></thead>
<tbody>
<tr><td rowspan="0">가</td><td>1</td></tr>
<tr><td>2</td></tr>
<tr><td>3</td></tr>
</tbody>
</table>""")

        errors, warnings = validate(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_short_body_rows_warn_with_table_and_first_row_lines(self):
        path = self.brief_with("""<table>
<thead><tr><th>항목</th><th>값</th><th>출처</th></tr></thead>
<tbody>
<tr><td>가</td><td>1</td><td>S1</td></tr>
<tr><td>나</td><td>2</td></tr>
<tr><td>다</td></tr>
</tbody>
</table>""")

        errors, warnings = validate(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["12줄 표의 머리는 3칸인데 본문 2개 줄의 칸 수가 다릅니다(첫 줄: 16줄 2칸)."])

    def test_wider_body_row_warns(self):
        path = self.brief_with("""<table>
<thead><tr><th>항목</th><th>값</th><th>출처</th></tr></thead>
<tbody><tr><td>가</td><td>1</td><td>S1</td><td>메모</td></tr></tbody>
</table>""")

        errors, warnings = validate(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["12줄 표의 머리는 3칸인데 본문 1개 줄의 칸 수가 다릅니다(첫 줄: 14줄 4칸)."])

    def test_rows_after_thead_without_tbody_are_body_rows(self):
        path = self.brief_with("""<table>
<thead><tr><th>항목</th><th>값</th></tr></thead>
<tr><td>가</td></tr>
</table>""")

        errors, warnings = validate(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["12줄 표의 머리는 2칸인데 본문 1개 줄의 칸 수가 다릅니다(첫 줄: 14줄 1칸)."])

    def test_header_cells_without_tr_are_counted(self):
        path = self.brief_with("""<table>
<thead><th>항목</th><th>값</th></thead>
<tbody><tr><td>가</td></tr></tbody>
</table>""")

        errors, warnings = validate(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["12줄 표의 머리는 2칸인데 본문 1개 줄의 칸 수가 다릅니다(첫 줄: 14줄 1칸)."])

    def test_body_row_header_cell_is_counted(self):
        path = self.brief_with("""<table>
<thead><tr><td></td><th>전</th><th>후</th></tr></thead>
<tbody><tr><th>가</th><td>1</td><td>2</td></tr></tbody>
</table>""")

        errors, warnings = validate(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_tfoot_rows_are_not_checked(self):
        path = self.brief_with("""<table>
<thead><tr><th>항목</th><th>값</th><th>출처</th></tr></thead>
<tbody><tr><td>가</td><td>1</td><td>S1</td></tr></tbody>
<tfoot><tr><td>합계 1</td></tr></tfoot>
</table>""")

        errors, warnings = validate(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_rows_without_own_cells_are_skipped(self):
        path = self.brief_with("""<table>
<thead><tr><th>항목</th><th>값</th></tr></thead>
<tbody>
<tr></tr>
<tr/><td>가</td><td>1</td>
</tbody>
</table>""")

        errors, warnings = validate(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_table_without_thead_is_not_checked(self):
        path = self.brief_with("""<table>
<tr><th>항목</th><th>값</th><th>출처</th></tr>
<tr><td>가</td></tr>
</table>""")

        errors, warnings = validate(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_nested_table_is_counted_separately(self):
        path = self.brief_with("""<table>
<thead><tr><th>항목</th><th>세부</th></tr></thead>
<tbody>
<tr><td>가</td><td>
<table>
<thead><tr><th>a</th><th>b</th><th>c</th></tr></thead>
<tbody><tr><td>1</td></tr></tbody>
</table>
</td></tr>
</tbody>
</table>""")

        errors, warnings = validate(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["16줄 표의 머리는 3칸인데 본문 1개 줄의 칸 수가 다릅니다(첫 줄: 18줄 1칸)."])

    def test_rows_without_end_tags_are_counted(self):
        path = self.brief_with("""<table>
<thead><tr><th>항목<th>값
<tbody>
<tr><td>가
<tr><td>나<td>2
</table>""")

        errors, warnings = validate(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["12줄 표의 머리는 2칸인데 본문 1개 줄의 칸 수가 다릅니다(첫 줄: 15줄 1칸)."])

    def test_span_values_follow_html_integer_rules(self):
        huge = "1" + "0" * 5000
        path = self.brief_with(f"""<table>
<thead><tr><th>a</th><th>b</th><th>c</th><th>d</th><th>e</th></tr></thead>
<tbody><tr><td colspan="0">1</td><td colspan=" 2">2</td><td colspan="+2">3</td></tr></tbody>
</table>
<table>
<thead><tr><th>a</th><th>b</th></tr></thead>
<tbody><tr><td colspan="２">1</td></tr></tbody>
</table>
<table>
<thead><tr><th>a</th><th>b</th></tr></thead>
<tbody><tr><td colspan="{huge}">1</td></tr></tbody>
</table>""")

        errors, warnings = validate(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [
            "16줄 표의 머리는 2칸인데 본문 1개 줄의 칸 수가 다릅니다(첫 줄: 18줄 1칸).",
            "20줄 표의 머리는 2칸인데 본문 1개 줄의 칸 수가 다릅니다(첫 줄: 22줄 1000칸).",
        ])


if __name__ == "__main__":
    unittest.main()
