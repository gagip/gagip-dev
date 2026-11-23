import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import session_doc  # noqa: E402

CSS = session_doc.CSS_PATH.read_text(encoding="utf-8")
SAMPLE = SCRIPTS.parent / "assets" / "sample.html"


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPTS / "session_doc.py"), *map(str, args)],
                          capture_output=True, text=True)


class NewAndCheck(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.doc = self.dir / "s.html"

    def test_new_doc_passes_check(self):
        self.assertEqual(run("new", self.doc, "--title", "시험").returncode, 0)
        r = run("check", self.doc)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_new_refuses_to_overwrite(self):
        self.doc.write_text("기존")
        self.assertEqual(run("new", self.doc, "--title", "시험").returncode, 2)
        self.assertEqual(self.doc.read_text(), "기존")

    def test_sync_restores_stale_css_and_sets_time(self):
        run("new", self.doc, "--title", "시험")
        text = session_doc.STYLE_RE.sub(
            lambda m: f"{m[1]}\n:root{{--primary:#000000}}\n{m[3]}",
            self.doc.read_text(),
            count=1,
        )
        text = session_doc.UPDATED_RE.sub(r"\g<1>옛 시각\g<3>", text)
        self.doc.write_text(text)
        self.assertEqual(run("check", self.doc).returncode, 1)
        self.assertEqual(run("sync", self.doc).returncode, 0)
        self.assertNotIn("옛 시각", self.doc.read_text())

    def test_sample_is_in_sync(self):
        self.assertEqual(session_doc.problems(SAMPLE.read_text(encoding="utf-8"), CSS), [])


class Problems(unittest.TestCase):
    def base(self):
        return session_doc.SKELETON.format(title="t", css=CSS, today="2026-01-01", now="2026-01-01 00:00")

    def test_missing_fixed_section(self):
        text = self.base().replace('id="flow"', 'id="steps"')
        self.assertTrue(any("#flow" in p for p in session_doc.problems(text, CSS)))

    def test_open_context_can_be_omitted_in_existing_documents(self):
        t = self.base().replace('<details id="context" open>\n<summary>목표·완료 기준과 진행 상태</summary>\n', "")
        t = t.replace('</ol>\n</details>', '</ol>')
        self.assertEqual(session_doc.problems(t, CSS), [])

    def test_decision_precedes_collapsed_context(self):
        decision = '<section id="decision"><h2>지금 고를 것</h2><a href="experiment.html">실험</a></section>'
        t = self.base().replace('<details id="context" open>', decision + '\n<details id="context">')
        self.assertEqual(session_doc.problems(t, CSS), [])

    def test_hidden_decision_is_rejected(self):
        decision = '<section id="decision"><h2>지금 검토할 것</h2></section>'
        t = self.base().replace(
            '<section id="spec"', decision + '<section id="spec"',
        ).replace('<details id="context" open>', '<details id="context">')
        self.assertTrue(any("#decision" in p for p in session_doc.problems(t, CSS)))

    def test_context_without_decision_starts_open(self):
        t = self.base().replace('<details id="context" open>', '<details id="context">')
        self.assertTrue(any("#context" in p for p in session_doc.problems(t, CSS)))

    def test_other_section_cannot_precede_decision(self):
        decision = '<section id="decision"><h2>지금 고를 것</h2></section>'
        t = self.base().replace(
            '<details id="context" open>', '<h2>참고</h2>' + decision + '<details id="context">',
        )
        self.assertTrue(any("바로 다음" in p for p in session_doc.problems(t, CSS)))

    def test_late_decision_is_rejected(self):
        decision = '<section id="decision"><h2>지금 검토할 것</h2></section>'
        t = self.base().replace('</main>', decision + '\n</main>')
        self.assertTrue(any("#decision" in p for p in session_doc.problems(t, CSS)))

    def test_wrong_order(self):
        t = self.base()
        spec = t[t.index('<section id="spec"'):t.index("</dl></section>") + len("</dl></section>")]
        t = t.replace(spec, "").replace('<section id="state">', spec + '\n<section id="state">')
        self.assertTrue(any("순서" in p for p in session_doc.problems(t, CSS)))

    def test_section_between_spec_and_flow(self):
        t = self.base().replace('<ol id="flow"', '<h2>끼어든 칸</h2>\n<ol id="flow"')
        self.assertTrue(any("사이" in p for p in session_doc.problems(t, CSS)))

    def test_state_needs_exactly_one_kind(self):
        t = self.base().replace('class="pill run"', 'class="pill"')
        self.assertTrue(any("상태 표시" in p for p in session_doc.problems(t, CSS)))

    def test_script_is_rejected(self):
        t = self.base().replace("</main>", "<script>1</script></main>")
        self.assertTrue(any("script" in p for p in session_doc.problems(t, CSS)))

    def test_card_and_chip_classes_are_rejected(self):
        for cls in session_doc.LEGACY_CLASSES:
            t = self.base().replace("</main>", f'<div class="x {cls}">a</div></main>')
            self.assertTrue(any("카드·칩" in p for p in session_doc.problems(t, CSS)), cls)

    def test_free_sections_after_flow_are_allowed(self):
        t = self.base().replace("</main>", '<h2>실험</h2><div class="compare"></div><ol class="ask"><li><span class="rec">권장</span></li></ol></main>')
        self.assertEqual(session_doc.problems(t, CSS), [])


if __name__ == "__main__":
    unittest.main()
