"""실제 Chrome으로 임시 HTML을 열어 판정을 확인한다. 외부 네트워크는 쓰지 않는다."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest

import check_page

SCRIPT = Path(check_page.__file__).resolve()
# 1x1 PNG
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360000002000001e221bc330000000049454e44ae426082"
)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/jump":
            self.send_response(302)
            self.send_header("Location", f"http://localhost:{self.server.server_port}/ok")
            self.end_headers()
        elif self.path == "/ok":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


class CheckPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def run_check(self, body: str):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "good.png").write_bytes(PNG)
            (root / "other.html").write_text("<p>다른 페이지</p>")
            page = root / "page.html"
            page.write_text(f"<!doctype html><html><body>{body}</body></html>")
            done = subprocess.run(
                ["uv", "run", str(SCRIPT), str(page), "--shots", str(root / "shots")],
                capture_output=True, text=True, timeout=120,
            )
            self.assertTrue(list((root / "shots").glob("*.png")) or done.returncode == 2, done.stderr)
            return done

    def assert_fails(self, body: str, expected: str):
        done = self.run_check(body)
        self.assertEqual(1, done.returncode, done.stdout + done.stderr)
        self.assertIn(f"[실패] {expected}", done.stdout)

    def test_정상_페이지는_통과한다(self):
        done = self.run_check(
            '<h1 id="top2">제목</h1><a href="#top2">위로</a><a href="other.html#x">다른</a>'
            f'<img src="good.png"><a href="{self.base}/ok">ok</a>'
        )
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        self.assertIn("실패 0개, 미확인 0개", done.stdout)

    def test_없는_앵커는_실패한다(self):
        self.assert_fails('<a href="#nowhere">x</a>', "앵커")

    def test_깨진_로컬_링크는_실패한다(self):
        self.assert_fails('<a href="missing.html">x</a>', "로컬 링크")

    def test_없는_이미지는_실패한다(self):
        self.assert_fails('<img src="missing.png">', "이미지")

    def test_콘솔_오류는_실패한다(self):
        self.assert_fails('<script>console.error("x")</script>', "콘솔 오류")

    def test_페이지_예외는_실패한다(self):
        self.assert_fails("<script>throw new Error('boom')</script>", "콘솔 오류")

    def test_다른_도메인으로_넘어가는_링크는_실패한다(self):
        self.assert_fails(f'<a href="{self.base}/jump">x</a>', "외부 링크")

    def test_외부_링크_404는_실패한다(self):
        self.assert_fails(f'<a href="{self.base}/nope">x</a>', "외부 링크")

    def test_네트워크_실패는_미확인이고_종료_코드는_0이다(self):
        done = self.run_check('<a href="http://127.0.0.1:1/">x</a>')
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        self.assertIn("[미확인] 외부 링크", done.stdout)
        self.assertIn("실패 0개, 미확인 1개", done.stdout)


class JudgementTests(unittest.TestCase):
    def test_종료_코드는_실패만_1이다(self):
        r = check_page.Result
        self.assertEqual(0, check_page.exit_code([r("a", check_page.OK, ""), r("b", check_page.UNCHECKED, "")]))
        self.assertEqual(1, check_page.exit_code([r("a", check_page.FAIL, "")]))

    def test_앵커가_아닌_값은_즉시_예외다(self):
        with self.assertRaises(ValueError):
            check_page.check_anchor("x.html", set())


if __name__ == "__main__":
    unittest.main()
