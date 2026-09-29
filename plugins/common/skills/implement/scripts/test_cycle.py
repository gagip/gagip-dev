"""임시 사이클과 실제 git으로 상태 전이·실패 무변경·재개를 확인한다."""

from __future__ import annotations

import contextlib
import fcntl
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cycle
import fixtures
import gate
import handoff
import test_gate


class CycleFixture:
    """임시 레포 위에 사이클을 깔고 전이를 돕는다. 테스트 클래스가 함께 상속한다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.repo = test_gate.make_repo(root)
        self.directory = fixtures.write_cycle(root / "cycle", {
            "cycle_id": "2026-08-31_test", "title": "상태 전이 테스트",
            "repo": str(self.repo), "branch": test_gate.BRANCH,
            "base": "main", "allow_main": "true",
        }, {})
        self.path = self.directory / "handoff.md"
        for name, text in test_gate.ARTIFACTS.values():
            (self.directory / name).write_text(text, encoding="utf-8")
        with self.path.open("a") as f:
            f.write("\n- 기존 질문과 다른 절은 보존한다.\n")

    def act(self, action, stage=None, **kw):
        return cycle.transition(self.directory, action, stage=stage,
                                decision="테스트에서 결정", **kw)

    def complete(self, key):
        return self.act("complete", key, artifact=test_gate.ARTIFACTS[key][0])

    def advance_to(self, key):
        for current in handoff.STAGE_KEYS:
            if current == key:
                break
            if current == "ship":
                self.act("skip", "ship")
            else:
                self.complete(current)

    def reject(self, callback, message):
        before = self.path.read_bytes()
        with self.assertRaisesRegex(cycle.TransitionError, message):
            callback()
        self.assertEqual(before, self.path.read_bytes())



class CycleTests(CycleFixture, unittest.TestCase):
    def corrupt_row(self, key, state):
        self.path.write_text(self.path.read_text().replace(
            f"| {key} | 미완 |  |", f"| {key} | {state} | {test_gate.ARTIFACTS[key][0]} |"))

    def test_existing_cycle_without_mode_is_read_only(self):
        before = self.path.read_bytes()
        h = cycle.inspect(self.directory)
        self.assertEqual("draft", cycle.mode(h))
        self.assertEqual("intake", h.first_incomplete().key)
        self.assertEqual(before, self.path.read_bytes())

    def test_successful_completion_and_restart_preserve_other_sections(self):
        self.complete("intake")
        h = cycle.inspect(self.directory)
        self.assertEqual("완료", h.stage("intake").state)
        self.assertEqual("branch", h.first_incomplete().key)
        self.assertIn("기존 질문과 다른 절은 보존한다.", self.path.read_text())
        self.assertIn("complete intake · 테스트에서 결정", self.path.read_text())

    def test_cannot_complete_a_later_stage(self):
        self.reject(lambda: self.complete("review"), "현재 단계")

    def test_current_gate_failure_does_not_write_completion(self):
        (self.directory / "00_intake.md").write_text("## 출처\n이슈 #12\n")
        self.reject(lambda: self.complete("intake"), "검증 조건")

    def test_prior_artifact_corruption_blocks_resume_and_next_completion(self):
        self.complete("intake")
        (self.directory / "00_intake.md").unlink()
        self.reject(lambda: cycle.inspect(self.directory), "산출물이 없다")
        self.reject(lambda: self.complete("branch"), "산출물이 없다")

    def test_live_git_branch_change_blocks_resume(self):
        self.advance_to("implement")
        test_gate._run(self.repo, "switch", "main")
        self.reject(lambda: cycle.inspect(self.directory), "현재 브랜치")

    def test_out_of_order_manually_completed_row_is_rejected(self):
        self.corrupt_row("review", "완료")
        self.reject(lambda: cycle.inspect(self.directory), "앞에 미완")

    def test_success_with_incomplete_stages_is_rejected(self):
        self.path.write_text(self.path.read_text().replace("status: 진행중", "status: 달성"))
        self.reject(lambda: cycle.inspect(self.directory), "미완 단계")

    def test_draft_cycle_can_skip_ship_and_close(self):
        self.advance_to("ship")
        self.act("skip", "ship")
        self.complete("close")
        h = cycle.inspect(self.directory)
        self.assertEqual("달성", h.meta["status"])
        self.assertEqual("생략", h.stage("ship").state)
        self.assertEqual("완료", h.stage("close").state)
        self.assertIsNone(h.first_incomplete())

    def add_commit(self, filename, *, subject="refactor: 작은 변경", author=None):
        (self.repo / filename).write_text("변경\n")
        test_gate._run(self.repo, "add", filename)
        args = ["commit", "-m", subject]
        if author:
            args = ["-c", f"user.email={author}", *args]
        test_gate._run(self.repo, *args)

    def test_incremental_commits_allow_dirty_work_in_each_phase(self):
        self.advance_to("implement")
        for key in ("implement", "simplify", "review", "docs"):
            (self.repo / key).write_text("작업 중\n")
            self.assertEqual(key, cycle.inspect(self.directory).first_incomplete().key)
            self.add_commit(key)
            self.complete(key)
        self.assertEqual("ship", cycle.inspect(self.directory).first_incomplete().key)
        before = gate._git(self.repo, "rev-parse", "HEAD")
        self.act("skip", "ship")
        self.complete("close")
        self.assertEqual(before, gate._git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual("5", gate._git(self.repo, "rev-list", "--count", "main..HEAD").strip())

    def test_dirty_work_blocks_submission_status_skip_and_complete(self):
        self.advance_to("ship")
        (self.repo / "pending").write_text("작업 중\n")
        self.reject(lambda: cycle.inspect(self.directory), "커밋되지 않은 변경")
        self.reject(lambda: self.act("skip", "ship"), "커밋되지 않은 변경")
        self.act("mode", new_mode="auto")
        self.reject(lambda: cycle.inspect(self.directory), "커밋되지 않은 변경")
        self.reject(lambda: self.complete("ship"), "커밋되지 않은 변경")
        self.act("stop")
        self.assertEqual("불가능", cycle.inspect(self.directory).meta["status"])
        self.assertTrue((self.repo / "pending").exists())

    def test_middle_commit_with_wrong_author_blocks_submission(self):
        self.advance_to("ship")
        self.add_commit("bad", author="wrong@example.com")
        self.add_commit("good")
        self.reject(lambda: cycle.inspect(self.directory), "커밋 작성자")
        self.reject(lambda: self.act("skip", "ship"), "커밋 작성자")
        self.act("mode", new_mode="auto")
        self.reject(lambda: self.complete("ship"), "커밋 작성자")

    def test_close_rechecks_changes_after_skipped_ship(self):
        self.advance_to("close")
        (self.repo / "pending").write_text("추가 수정\n")
        self.reject(lambda: cycle.inspect(self.directory), "커밋되지 않은 변경")
        self.reject(lambda: self.complete("close"), "커밋되지 않은 변경")
        self.add_commit("pending", author="wrong@example.com")
        self.reject(lambda: cycle.inspect(self.directory), "커밋 작성자")
        self.reject(lambda: self.complete("close"), "커밋 작성자")
        self.assertEqual("진행중", handoff.load(self.directory).meta["status"])

    def test_completed_cycle_still_checks_commits(self):
        self.advance_to("close")
        self.complete("close")
        self.add_commit("bad", author="wrong@example.com")
        self.reject(lambda: cycle.inspect(self.directory), "커밋 작성자")

    def test_commit_check_handles_git_errors_without_writing(self):
        self.advance_to("ship")
        original_git = gate._git

        def missing_config(repo, *args):
            if args == ("config", "user.email"):
                raise gate.GateError("git 설정 조회 실패")
            return original_git(repo, *args)

        with patch.object(gate, "_git", side_effect=missing_config):
            self.reject(lambda: cycle.inspect(self.directory), "git 설정 조회 실패")
            self.reject(lambda: self.act("skip", "ship"), "git 설정 조회 실패")
        self.path.write_text(self.path.read_text().replace("base: main", "base: missing-base"))
        ok, reasons = gate.check_commits(handoff.load(self.directory))
        self.assertFalse(ok)
        self.assertIn("missing-base", " ".join(reasons))
        self.reject(lambda: cycle.inspect(self.directory), "missing-base")
        self.reject(lambda: self.act("skip", "ship"), "missing-base")

    def test_legacy_commit_row_requires_migration_without_losing_evidence(self):
        old_row = "| commit | 미완 | 06_commit.md |\n"
        (self.directory / "06_commit.md").write_text("기존 커밋 기록\n")
        self.path.write_text(self.path.read_text().replace("| ship |", old_row + "| ship |"))
        before = self.path.read_bytes()
        for callback in (lambda: cycle.inspect(self.directory), lambda: self.complete("intake")):
            with self.assertRaisesRegex(handoff.HandoffError, "commit 행만 제거"):
                callback()
            self.assertEqual(before, self.path.read_bytes())
        self.path.write_text(self.path.read_text().replace(old_row, "").replace(
            "## 결정 로그\n", "## 결정 로그\n\n- 이전 커밋 근거: 06_commit.md\n"))
        self.assertEqual("intake", cycle.inspect(self.directory).first_incomplete().key)
        self.complete("intake")
        self.assertIn("이전 커밋 근거: 06_commit.md", self.path.read_text())
        self.assertEqual("기존 커밋 기록\n", (self.directory / "06_commit.md").read_text())

    def test_cannot_skip_ship_early_or_any_other_stage(self):
        self.reject(lambda: self.act("skip", "ship"), "현재 단계")
        self.reject(lambda: self.act("skip", "intake"), "ship만")

    def test_auto_requires_ship_evidence_and_cannot_skip(self):
        self.act("mode", new_mode="auto")
        self.advance_to("ship")
        self.reject(lambda: self.act("skip", "ship"), "ship만")
        (self.directory / "07_ship.md").write_text("제출 예정\n")
        self.reject(lambda: self.complete("ship"), "PR URL")
        (self.directory / "07_ship.md").write_text(test_gate.SHIP_GOOD)
        self.complete("ship")
        self.complete("close")
        self.assertEqual("달성", cycle.inspect(self.directory).meta["status"])

    def test_draft_cannot_complete_ship(self):
        self.advance_to("ship")
        self.reject(lambda: self.complete("ship"), "auto 모드")

    def test_skipped_ship_cannot_be_changed_to_auto(self):
        self.advance_to("ship")
        self.act("skip", "ship")
        self.reject(lambda: self.act("mode", new_mode="auto"), "이미 처리")

    def test_legacy_draft_skip_marker_can_precede_pending_stages(self):
        self.corrupt_row("ship", "생략")
        self.assertEqual("intake", cycle.inspect(self.directory).first_incomplete().key)
        self.reject(lambda: self.act("mode", new_mode="auto"), "이미 처리")

    def test_manual_auto_skip_is_rejected(self):
        self.act("mode", new_mode="auto")
        self.corrupt_row("ship", "생략")
        self.reject(lambda: cycle.inspect(self.directory), "auto 모드")

    def test_failed_close_preserves_open_status_and_incomplete_close(self):
        self.advance_to("close")
        (self.directory / "08_close.md").write_text("## 종결\n검사 실패\n")
        self.reject(lambda: self.complete("close"), "달성")
        h = handoff.load(self.directory)
        self.assertEqual("진행중", h.meta["status"])
        self.assertEqual("미완", h.stage("close").state)

    def test_stop_does_not_require_a_failing_prior_gate_to_pass(self):
        self.complete("intake")
        (self.directory / "00_intake.md").unlink()
        before_states = handoff.load(self.directory).stages
        self.act("stop")
        h = cycle.inspect(self.directory)
        self.assertEqual("불가능", h.meta["status"])
        self.assertEqual(before_states, h.stages)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            cycle.show(h)
        self.assertNotIn("다음 할 단계:", output.getvalue())

    def test_terminal_cycle_rejects_all_mutations(self):
        self.act("stop")
        for action, kwargs in (("complete", {"stage": "intake"}),
                               ("skip", {"stage": "ship"}),
                               ("mode", {"new_mode": "auto"}), ("stop", {})):
            with self.subTest(action=action):
                self.reject(lambda: self.act(action, **kwargs), "종결된")

    def test_decision_must_fit_a_single_log_entry(self):
        for value in ("", "한 줄\n두 줄", "a" * 201):
            with self.subTest(value=value):
                self.reject(lambda: cycle.transition(self.directory, "stop", decision=value), "결정")

    def test_artifact_must_be_a_local_file(self):
        external = self.directory.parent / "external.md"
        external.write_text(test_gate.INTAKE_GOOD)
        (self.directory / "linked.md").symlink_to(external)
        for value in ("../external.md", str(external), "linked.md", "handoff.md", "missing.md", "."):
            with self.subTest(value=value):
                self.reject(lambda: self.act("complete", "intake", artifact=value), "산출물|handoff.md")

    def test_artifact_surrounding_whitespace_is_rejected_before_save(self):
        (self.directory / " 00_intake.md ").write_text(test_gate.INTAKE_GOOD)
        self.reject(lambda: self.act("complete", "intake", artifact=" 00_intake.md "), "산출물")

    def test_existing_heading_levels_remain_writable(self):
        self.path.write_text(self.path.read_text().replace("## 진행", "### 진행")
                             .replace("## 결정 로그", "### 결정 로그"))
        self.assertEqual("intake", cycle.inspect(self.directory).first_incomplete().key)
        self.complete("intake")
        self.assertEqual("branch", cycle.inspect(self.directory).first_incomplete().key)
        self.assertIn("### 진행", self.path.read_text())
        self.assertIn("### 결정 로그", self.path.read_text())

    def test_replace_failure_keeps_original_and_removes_tempfile(self):
        before = self.path.read_bytes()
        with patch.object(cycle.os, "replace", side_effect=OSError("disk error")):
            with self.assertRaisesRegex(OSError, "disk error"):
                self.complete("intake")
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual([], list(self.directory.glob(".handoff-*")))

    def test_external_edit_during_validation_is_not_overwritten(self):
        old_check = gate.check_stage
        changed = self.path.read_text() + "\n- 검사 중 사용자가 추가한 질문\n"

        def concurrent_edit(h, key, **kwargs):
            self.path.write_text(changed)
            return old_check(h, key)

        with patch.object(gate, "check_stage", side_effect=concurrent_edit):
            with self.assertRaisesRegex(cycle.TransitionError, "검증 중"):
                self.complete("intake")
        self.assertEqual(changed, self.path.read_text())
        self.assertEqual([], list(self.directory.glob(".handoff-*")))

    def test_competing_process_cannot_save_while_locked(self):
        before = self.path.read_bytes()
        fd = os.open(self.directory, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run([
                sys.executable, "-B", str(Path(cycle.__file__)), str(self.directory),
                "complete", "intake", "--artifact", "00_intake.md", "--decision", "동시 실행",
            ], text=True, capture_output=True)
        finally:
            os.close(fd)
        self.assertEqual(1, result.returncode)
        self.assertIn("다른 상태 변경", result.stderr)
        self.assertEqual(before, self.path.read_bytes())
        self.complete("intake")
        self.reject(lambda: self.complete("intake"), "현재 단계")

    def test_cli_status_and_complete_round_trip(self):
        cmd = [sys.executable, "-B", str(Path(cycle.__file__)), str(self.directory)]
        result = subprocess.run(cmd + ["complete", "intake", "--artifact", "00_intake.md",
                                       "--decision", "CLI 검증"], text=True, capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("다음 할 단계: branch", result.stdout)
        result = subprocess.run(cmd + ["status"], text=True, capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("다음 할 단계: branch", result.stdout)


class PlanTransitionTests(CycleFixture, unittest.TestCase):
    """계획서 파일 존재는 접수 완료 전이 때만 본다."""

    def set_plan(self, value: str) -> None:
        text = self.path.read_text(encoding="utf-8")
        self.path.write_text(text.replace("plan:\n", f"plan: {value}\n", 1), encoding="utf-8")

    def test_missing_plan_file_blocks_intake(self):
        self.set_plan(str(Path(self.tmp.name) / "없는계획서.md"))
        self.reject(lambda: self.complete("intake"), "계획서 파일이 없다")

    def test_existing_plan_passes_and_later_removal_keeps_status(self):
        plan = Path(self.tmp.name) / "plan.md"
        plan.write_text("# 계획\n", encoding="utf-8")
        self.set_plan(str(plan))
        self.complete("intake")
        plan.unlink()
        self.assertEqual("완료", cycle.inspect(self.directory).stage("intake").state)


class MainBranchRepoTests(unittest.TestCase):
    """main에 직접 커밋하는 저장소는 base에 시작 시점 해시를 적어 커밋 범위를 잡는다."""

    def test_hash_base_counts_commits_on_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = test_gate.make_repo(root, empty=True)
            test_gate._run(repo, "switch", "main")
            start = gate._git(repo, "rev-parse", "HEAD").strip()
            (repo / "a.txt").write_text("base\n변경\n", encoding="utf-8")
            test_gate._run(repo, "commit", "-am", "작은 변경")
            meta = {"branch": "main", "allow_main": "true"}
            for base, ok in ((start, True), ("main", False)):
                with self.subTest(base=base):
                    cycle_dir = test_gate.make_cycle(root / f"cycle-{ok}", repo,
                                                     meta={**meta, "base": base})
                    passed, reasons = gate.check_commits(handoff.load(cycle_dir))
                    self.assertEqual(ok, passed, reasons)


class InitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_creates_cycle_from_template(self):
        plan = self.root / "plan.md"
        plan.write_text("# 계획\n", encoding="utf-8")
        h = cycle.init(self.root / "2026-10-01_login", "로그인 문구 수정", str(plan))
        self.assertEqual("2026-10-01_login", h.meta["cycle_id"])
        self.assertEqual("로그인 문구 수정", h.meta["title"])
        self.assertEqual(str(plan.resolve()), h.meta["plan"])
        self.assertEqual("intake", h.first_incomplete().key)

    def test_relative_plan_is_stored_absolute(self):
        (self.root / "plan.md").write_text("# 계획\n", encoding="utf-8")
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.root)
        h = cycle.init(self.root / "2026-10-01_rel", "상대경로", "plan.md")
        self.assertTrue(Path(h.meta["plan"]).is_absolute())

    def test_empty_plan_line_without_plan(self):
        h = cycle.init(self.root / "2026-10-01_small", "작은 작업")
        self.assertEqual("", h.meta["plan"])

    def test_backslashes_in_title_and_plan_are_kept_literally(self):
        plan_dir = self.root / "p\\new"
        plan_dir.mkdir()
        plan = plan_dir / "plan.md"
        plan.write_text("# 계획\n", encoding="utf-8")
        title = r"fix \n parse \d \1"
        h = cycle.init(self.root / "2026-10-01_esc", title, str(plan))
        self.assertEqual(title, h.meta["title"])
        self.assertEqual(str(plan.resolve()), h.meta["plan"])

    def test_rejects_folder_dated_before_rule(self):
        with self.assertRaisesRegex(cycle.TransitionError, "이후여야"):
            cycle.init(self.root / "2020-01-01_old", "옛 날짜")
        self.assertFalse((self.root / "2020-01-01_old").exists())

    def test_rejects_existing_folder_missing_plan_and_bad_name(self):
        (self.root / "2026-10-01_dup").mkdir()
        for args, message in (
            ((self.root / "2026-10-01_dup", "중복"), "이미 있는"),
            ((self.root / "2026-10-01_x", "계획 없음", str(self.root / "없음.md")), "계획서 파일이 없다"),
            ((self.root / "login", "이름 형식"), "YYYY-MM-DD"),
            ((self.root / "2026-10-01_blank", "  "), "한 줄"),
            ((self.root / "2026-10-01_lines", "첫 줄\n둘째 줄"), "한 줄"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(cycle.TransitionError, message):
                    cycle.init(*args)
        self.assertFalse((self.root / "2026-10-01_x").exists())


if __name__ == "__main__":
    unittest.main()
