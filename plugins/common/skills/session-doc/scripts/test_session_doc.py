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
        text = self.doc.read_text().replace("--primary:#4f46e5", "--primary:#000000", 1)
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

    def test_free_sections_after_flow_are_allowed(self):
        t = self.base().replace("</main>", '<h2>실험</h2><div class="compare"></div></main>')
        self.assertEqual(session_doc.problems(t, CSS), [])


if __name__ == "__main__":
    unittest.main()
