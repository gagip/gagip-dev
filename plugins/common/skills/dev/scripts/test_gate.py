"""증거 문턱이 기록 없는 PR 생성·머지를 막고, 맞는 기록만 통과시키는지 임시 저장소로 확인한다."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import gate


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


class GateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        origin = self.root / "origin.git"
        git(self.root, "init", "--bare", "-b", "main", str(origin))
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "dev@example.com")
        git(self.repo, "config", "user.name", "Dev")
        (self.repo / "a.py").write_text("x = 1\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "chore: 초기")
        git(self.repo, "remote", "add", "origin", str(origin))
        git(self.repo, "push", "-q", "origin", "main")
        git(self.repo, "remote", "set-url", "origin", "git@github.com:Owner/App.git")
        git(self.repo, "update-ref", "refs/remotes/origin/main", "main")
        git(self.repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        git(self.repo, "switch", "-q", "-c", "feat/x")
        (self.repo / "a.py").write_text("x = 2\n")
        git(self.repo, "commit", "-qam", "feat: 변경")
        self.command = [sys.executable, "-c", "print('ok')"]
        config = self.root / "gate.json"
        config.write_text(json.dumps({"repos": {"owner/app": {"conditions": {"테스트": self.command}}}}))
        self.report = self.root / "review.md"
        self.report.write_text("검토 결과\n")
        env = {"EVIDENCE_GATE_CONFIG": str(config), "EVIDENCE_GATE_ROOT": str(self.root / "evidence")}
        patcher = patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.dir = gate.evidence_dir("owner/app", "feat/x")

    def event(self, command, cwd=None):
        return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd or self.repo)}

    def decision(self, command, harness="claude", cwd=None):
        out = gate.decide(self.event(command, cwd), harness)
        return out.get("hookSpecificOutput", {}).get("permissionDecision")

    def record_all(self, command=None):
        gate.verify.record(self.repo, self.dir, "테스트", command or self.command)
        gate.verify.record(self.repo, self.dir, gate.REVIEW, [*gate.REVIEW_COMMAND, str(self.report)])

    def test_create_without_evidence_asks_on_claude_and_denies_on_codex(self):
        self.assertEqual("ask", self.decision("gh pr create --fill"))
        self.assertEqual("deny", self.decision("gh pr create --fill", harness="codex"))

    def test_create_with_current_evidence_passes(self):
        self.record_all()
        self.assertIsNone(self.decision("gh pr create --fill"))

    def test_review_is_required(self):
        gate.verify.record(self.repo, self.dir, "테스트", self.command)
        self.assertEqual("ask", self.decision("gh pr create --fill"))

    def test_stale_evidence_after_code_change(self):
        self.record_all()
        (self.repo / "a.py").write_text("x = 3\n")
        self.assertEqual("ask", self.decision("gh pr create --fill"))

    def test_other_command_does_not_count(self):
        self.record_all(command=["echo", "ok"])
        self.assertEqual("ask", self.decision("gh pr create --fill"))

    def test_docs_only_change_is_exempt(self):
        git(self.repo, "reset", "-q", "--hard", "main")
        (self.repo / "README.md").write_text("문서\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "docs: 문서")
        self.assertIsNone(self.decision("gh pr create --fill"))

    def test_untargeted_repo_and_non_mutating_commands_pass(self):
        git(self.repo, "remote", "set-url", "origin", "git@github.com:someone/else.git")
        self.assertIsNone(self.decision("gh pr create --fill"))
        git(self.repo, "remote", "set-url", "origin", "git@github.com:Owner/App.git")
        self.assertIsNone(self.decision("gh pr view 3"))
        self.assertIsNone(self.decision('echo "gh pr create"'))

    def test_chained_and_cd_commands_are_seen(self):
        self.assertEqual("ask", self.decision(f"git push -u origin feat/x && gh pr create --fill"))
        self.assertEqual("ask", self.decision(f"cd {self.repo} && gh pr create --fill", cwd=self.root))

    def test_wrapped_and_multiline_commands_are_seen(self):
        for command in ("git push\ngh pr create --fill", "FOO=1 gh pr create --fill", "env X=1 gh pr create",
                        "sudo gh pr create", "if true; then gh pr create; fi", "bash -c 'gh pr create --fill'",
                        "gh pr create --fill --body \"it's done"):
            self.assertEqual("ask", self.decision(command), command)

    def test_create_rejects_evidence_from_dirty_tree(self):
        (self.repo / "b.py").write_text("y = 1\n")
        self.record_all()
        self.assertEqual("ask", self.decision("gh pr create --fill"))

    def test_create_for_target_repo_from_outside_its_tree_asks(self):
        self.assertEqual("ask", self.decision("gh pr create -R owner/app --fill", cwd=self.root))

    def pr_view(self, head, files=("a.py",)):
        data = {"headRefName": "feat/x", "headRefOid": head, "files": [{"path": p} for p in files]}
        return subprocess.CompletedProcess([], 0, stdout=json.dumps(data), stderr="")

    def test_merge_checks_pr_head_from_any_folder(self):
        head = git(self.repo, "rev-parse", "HEAD").strip()
        with patch.object(gate.subprocess, "run", side_effect=lambda *a, **k: self.pr_view(head)):
            self.assertEqual("ask", self.decision("gh pr merge 5 -R owner/app --squash", cwd=self.root))
        self.record_all()
        with patch.object(gate.subprocess, "run", side_effect=lambda *a, **k: self.pr_view(head)):
            self.assertIsNone(self.decision("gh pr merge 5 -R owner/app --squash", cwd=self.root))
        with patch.object(gate.subprocess, "run", side_effect=lambda *a, **k: self.pr_view("0" * 40)):
            self.assertEqual("ask", self.decision("gh pr merge 5 -R owner/app --squash", cwd=self.root))

    def test_merge_rejects_evidence_from_dirty_tree(self):
        (self.repo / "b.py").write_text("y = 1\n")
        self.record_all()
        head = git(self.repo, "rev-parse", "HEAD").strip()
        with patch.object(gate.subprocess, "run", side_effect=lambda *a, **k: self.pr_view(head)):
            self.assertEqual("ask", self.decision("gh pr merge 5 -R owner/app", cwd=self.root))

    def test_merge_docs_only_pr_is_exempt(self):
        with patch.object(gate.subprocess, "run", side_effect=lambda *a, **k: self.pr_view("1" * 40, ("docs/a.png", "b.md"))):
            self.assertIsNone(self.decision("gh pr merge 5 -R owner/app", cwd=self.root))

    def test_hook_error_blocks(self):
        Path(os.environ["EVIDENCE_GATE_CONFIG"]).write_text("{깨진 json")
        script = Path(gate.__file__)
        result = subprocess.run([sys.executable, str(script), "hook"], input=json.dumps(self.event("gh pr create")),
                                capture_output=True, text=True, cwd=self.repo)
        self.assertEqual("deny", json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"])


if __name__ == "__main__":
    unittest.main()
