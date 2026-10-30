"""실제 임시 Git 저장소에서 거짓 완료·오래된 증거·회귀를 확인한다."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

import verify


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def make_repo(root):
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "dev@example.com")
    git(repo, "config", "user.name", "Dev")
    (repo / "a.txt").write_text("base")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "chore: 초기 상태")
    return repo


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.repo = make_repo(root)
        self.root = root
        self.evidence = root / "evidence"
        self.condition = "기대 동작을 확인한다"

    def check(self):
        return verify.check(self.repo, self.evidence, [self.condition])

    def run_check(self, source="print('ok')", **kw):
        return verify.record(self.repo, self.evidence, self.condition, [sys.executable, "-c", source], **kw)

    def test_missing_evidence_blocks_claimed_success(self):
        self.assertTrue(self.check())

    def test_success_and_log(self):
        result = self.run_check()
        self.assertEqual("passed", result["status"])
        self.assertEqual([], self.check())
        self.assertEqual("ok\n", (self.evidence / result["log"]).read_text())

    def test_failure_replaces_old_success(self):
        self.run_check()
        result = self.run_check("raise SystemExit(3)")
        self.assertEqual(3, result["exit_code"])
        self.assertTrue(self.check())

    def test_code_change_after_success_is_stale(self):
        self.run_check()
        (self.repo / "a.txt").write_text("different")
        self.assertTrue(self.check())

    def test_untracked_change_is_stale(self):
        self.run_check()
        (self.repo / "new.txt").write_text("new")
        self.assertTrue(self.check())

    def test_commit_same_content_keeps_evidence(self):
        (self.repo / "new.txt").write_text("new")
        self.run_check()
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "feat: 내용 저장")
        self.assertEqual([], self.check())

    def test_committed_deletion_keeps_evidence(self):
        (self.repo / "a.txt").unlink()
        self.run_check()
        git(self.repo, "add", "-u")
        self.assertEqual([], self.check())
        git(self.repo, "commit", "-m", "fix: 파일 삭제")
        self.assertEqual([], self.check())

    def test_concurrent_condition_is_rejected_and_running_record_not_reused(self):
        self.run_check()
        entered, release = Event(), Event()
        original = verify._record

        def delayed(*args, **kwargs):
            entered.set()
            release.wait(5)
            return original(*args, **kwargs)

        with ThreadPoolExecutor(max_workers=1) as pool, patch.object(verify, "_record", delayed):
            future = pool.submit(self.run_check)
            self.assertTrue(entered.wait(5))
            try:
                self.assertTrue(self.check())
                with self.assertRaisesRegex(ValueError, "실행 중"):
                    self.run_check("raise SystemExit(1)")
            finally:
                release.set()
            self.assertEqual("passed", future.result()["status"])

    def test_changed_condition_and_log_rejected(self):
        result = self.run_check()
        (self.evidence / result["log"]).write_text("forged")
        self.assertTrue(self.check())
        self.run_check()
        self.condition = "다른 동작을 확인한다"
        self.assertTrue(self.check())

    def test_command_mutating_code_is_not_success(self):
        result = self.run_check("from pathlib import Path; Path('a.txt').write_text('oops')")
        self.assertEqual("changed", result["status"])
        self.assertTrue(self.check())

    def test_unavailable_command_and_timeout(self):
        result = verify.record(self.repo, self.evidence, self.condition, ["/nonexistent-executable"])
        self.assertEqual("not-run", result["status"])
        self.assertTrue(self.check())
        result = self.run_check("import time; time.sleep(30)", timeout=0.05)
        self.assertEqual("timeout", result["status"])
        self.assertTrue(self.check())

    def test_manual_confirmation_is_distinct(self):
        self.condition = "화면 문구 사람 확인"
        with self.assertRaises(ValueError):
            self.run_check()
        with self.assertRaises(ValueError):
            verify.record(self.repo, self.evidence, self.condition, [])
        verify.record(self.repo, self.evidence, self.condition, [], source="사용자 메시지: 문구를 확인함", observation="예상 문구 표시")
        self.assertEqual([], self.check())

    def test_evidence_inside_repository_rejected(self):
        with self.assertRaises(ValueError):
            verify.record(self.repo, self.repo / "evidence", self.condition, [sys.executable, "-c", "pass"])

    def test_malformed_record_fails_closed(self):
        self.run_check()
        path = self.evidence / f"{verify.key(self.condition)}.json"
        for data in ("[]", "null", "{broken"):
            path.write_text(data)
            self.assertTrue(self.check())

    def test_cli_options_and_failed_exit(self):
        script = str(Path(verify.__file__).resolve())
        args = [sys.executable, script, "run", "--repo", str(self.repo), "--evidence", str(self.evidence), "--condition", self.condition, "--", sys.executable, "-c"]
        self.assertEqual(0, subprocess.run(args + ["print('ok')"], capture_output=True).returncode)
        self.assertEqual(1, subprocess.run(args + ["raise SystemExit(1)"], capture_output=True).returncode)

    def test_interrupted_retry_does_not_reuse_previous_success(self):
        self.run_check()
        script = str(Path(verify.__file__).resolve())
        command = "import os, signal, time; os.kill(os.getppid(), signal.SIGINT); time.sleep(0.2)"
        proc = subprocess.run([sys.executable, script, "run", "--repo", str(self.repo), "--evidence", str(self.evidence), "--condition", self.condition, "--",
                               sys.executable, "-c", command], capture_output=True)
        self.assertNotEqual(0, proc.returncode)
        self.assertTrue(self.check())

    def test_regression_assertion_fails_before_fix_passes_after(self):
        self.run_check("from pathlib import Path; assert 'fixed' in Path('a.txt').read_text()")
        self.assertTrue(self.check())
        (self.repo / "a.txt").write_text("fixed")
        self.run_check("from pathlib import Path; assert 'fixed' in Path('a.txt').read_text()")
        self.assertEqual([], self.check())


if __name__ == "__main__":
    unittest.main()
