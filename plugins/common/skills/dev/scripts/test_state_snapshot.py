"""가짜 명령 실행기·HTTP 호출로 정상·실패·설정 없음·PR 없음을 확인한다."""
import contextlib
import io
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

import state_snapshot as snap

PR = {"number": 7, "state": "OPEN", "headRefName": "feat/x", "headRefOid": "abc", "mergedAt": None,
      "url": "https://example.com/pr/7"}
TAGS = "aaa\trefs/tags/v1.2.0\nbbb\trefs/tags/v1.10.0\nccc\trefs/tags/v1.10.0^{}\nddd\trefs/tags/v1.9.0\n"


class FakeRun:
    def __init__(self, overrides=None):
        self.calls = []
        self.overrides = overrides or {}

    def __call__(self, args, cwd):
        self.calls.append(args)
        for prefix, reply in self.overrides.items():
            if " ".join(args).startswith(prefix):
                return reply
        joined = " ".join(args)
        if joined.startswith("gh pr view"):
            return 0, json.dumps(PR), ""
        if joined.startswith("gh pr checks"):
            return 8, json.dumps([{"name": "ci", "state": "PENDING", "bucket": "pending", "link": ""}]), ""
        if joined.startswith("git ls-remote"):
            return 0, TAGS, ""
        if joined.startswith("git rev-parse"):
            return 0, "main\n", ""
        if joined.startswith("gh run list"):
            return 0, "[]", ""
        raise AssertionError(joined)


def ok_get(url, timeout):
    return {"status": 200, "elapsed_ms": 12, "body": "ok"}


NOW = lambda: datetime(2026, 11, 5, 1, 2, 3, tzinfo=timezone.utc)  # noqa: E731


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.missing_config = self.dir / "none.json"

    def take(self, run=None, get=ok_get, config=None, pr=""):
        return snap.snapshot(self.dir, pr, config or self.missing_config, run or FakeRun(), get, NOW)

    def write_config(self, servers):
        path = self.dir / "cfg.json"
        path.write_text(json.dumps({"servers": servers}))
        return path

    def test_normal_collects_everything_with_time(self):
        result = self.take(config=self.write_config({"api": "http://x.test/health"}))
        items = result["items"]
        self.assertEqual(result["collected_at_utc"], "2026-11-05T01:02:03+00:00")
        self.assertEqual(items["pr"]["result"]["number"], 7)
        self.assertEqual(items["ci"]["result"][0]["state"], "PENDING")
        self.assertEqual(items["server:api"]["result"]["status"], 200)
        self.assertTrue(all(item["ok"] for item in items.values()))

    def test_tags_use_version_order_and_peeled_sha(self):
        tags = self.take()["items"]["tags"]["result"]
        self.assertEqual([t["name"] for t in tags["latest_by_version"]], ["v1.2.0", "v1.9.0", "v1.10.0"])
        self.assertEqual(tags["latest_by_version"][-1]["sha"], "ccc")

    def test_no_pr_is_recorded_not_failed_and_ci_falls_back_to_runs(self):
        run = FakeRun({"gh pr view": (1, "", 'no pull requests found for branch "main"')})
        result = self.take(run)
        self.assertTrue(result["items"]["pr"]["ok"])
        self.assertIsNone(result["items"]["pr"]["result"])
        self.assertIn("PR 없음", result["items"]["pr"]["note"])
        self.assertTrue(any(c[:3] == ["gh", "run", "list"] for c in run.calls))

    def test_pr_arg_is_passed_to_gh(self):
        run = FakeRun()
        self.take(run, pr="feat/x")
        self.assertIn(["gh", "pr", "view", "feat/x", "--json", "number,state,headRefName,headRefOid,mergedAt,url"], run.calls)

    def test_failure_is_recorded_and_others_still_collected(self):
        run = FakeRun({"gh pr view": (1, "", "gh: not logged in")})
        result = self.take(run)
        self.assertFalse(result["items"]["pr"]["ok"])
        self.assertIn("not logged in", result["items"]["pr"]["error"])
        self.assertTrue(result["items"]["tags"]["ok"])

    def test_missing_config_is_skipped_as_not_configured(self):
        item = self.take()["items"]["servers"]
        self.assertTrue(item["ok"])
        self.assertEqual(item["note"], "설정 없음")

    def test_server_failure_does_not_stop_other_servers(self):
        def get(url, timeout):
            if "bad" in url:
                raise TimeoutError("timed out")
            return ok_get(url, timeout)

        items = self.take(get=get, config=self.write_config({"bad": "http://bad.test", "good": "http://good.test"}))["items"]
        self.assertFalse(items["server:bad"]["ok"])
        self.assertIn("TimeoutError", items["server:bad"]["error"])
        self.assertTrue(items["server:good"]["ok"])

    def test_broken_config_is_a_failure(self):
        path = self.dir / "cfg.json"
        path.write_text("{not json")
        self.assertFalse(self.take(config=path)["items"]["servers"]["ok"])

    def test_commands_are_read_only(self):
        run = FakeRun()
        self.take(run)
        for call in run.calls:
            self.assertNotIn(call[1:3], (["pr", "edit"], ["pr", "merge"], ["pr", "create"]))
            self.assertNotIn("push", call)
            self.assertNotIn("fetch", call)


class MainTests(unittest.TestCase):
    def test_exit_code_and_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "sub" / "snap.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = snap.main(["--out", str(out), "--repo", tmp, "--config", str(Path(tmp) / "none.json")],
                                 FakeRun({"gh pr view": (1, "", "boom")}), ok_get)
            self.assertEqual(code, 1)
            self.assertFalse(json.loads(out.read_text())["items"]["pr"]["ok"])


class HttpGetTests(unittest.TestCase):
    def test_http_error_status_is_a_result(self):
        import http.server
        import threading

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b"x" * 1000)

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        result = snap.http_get(f"http://127.0.0.1:{server.server_port}/", 5)
        self.assertEqual(result["status"], 503)
        self.assertEqual(len(result["body"]), snap.BODY_BYTES)


if __name__ == "__main__":
    unittest.main()
