"""산출물 보존(.eval-runs)과 바뀐 파일 판별을 LLM 호출 없이 확인한다."""
import json
from pathlib import Path
import tempfile
import unittest

import _artifacts
from _harness import CaseResult, RunCost, RunResult, snapshot_files


class RunsRootTests(unittest.TestCase):
    def test_uses_nearest_repo_root_from_a_subdirectory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            (repo / ".git").mkdir()
            deep = repo / "plugins" / "p" / "skills" / "s"
            deep.mkdir(parents=True)
            self.assertEqual(repo / ".eval-runs", _artifacts.find_runs_root(deep))


class ChangedFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "keep.txt").write_text("a")
        (self.root / "edit.txt").write_text("a")
        (self.root / ".git").mkdir()
        self.run = RunResult(True, workdir=self.root, snapshot=snapshot_files(self.root))

    def test_new_and_modified_files_only(self):
        (self.root / "edit.txt").write_text("b")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "new.md").write_text("n")
        (self.root / ".git" / "HEAD").write_text("ref")
        self.assertEqual(["docs/new.md", "edit.txt"], self.run.changed_files())

    def test_discard_removes_workdir(self):
        self.run.discard()
        self.assertFalse(self.root.exists())
        self.assertEqual([], self.run.changed_files())


class SaveCaseTests(unittest.TestCase):
    def test_writes_case_runs_baseline_and_changed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "work"
            work.mkdir()
            run = RunResult(False, reason="check 실패: x", final_text="끝", workdir=work,
                            snapshot=snapshot_files(work), cost=RunCost(turns=2))
            (work / "docs").mkdir()
            (work / "docs" / "a.md").write_text("본문", encoding="utf-8")
            cr = CaseResult("c", [run], baseline=[RunResult(True)], model="sonnet")

            case_dir = _artifacts.save_case(Path(tmp) / "runs", "demo", cr, {"verdict": "FAIL"},
                                            run_extras=[{"llm": {"ok": True}}])

            self.assertEqual(Path(tmp) / "runs" / "demo" / "c@sonnet", case_dir)
            self.assertEqual("FAIL", json.loads((case_dir / "case.json").read_text())["verdict"])
            record = json.loads((case_dir / "run1" / "result.json").read_text())
            self.assertEqual(["docs/a.md"], record["changed_files"])
            self.assertEqual(2, record["cost"]["turns"])
            self.assertEqual({"ok": True}, record["llm"])
            self.assertEqual("본문", (case_dir / "run1" / "files" / "docs" / "a.md").read_text(encoding="utf-8"))
            self.assertEqual("끝", (case_dir / "run1" / "final.md").read_text(encoding="utf-8"))
            self.assertTrue((case_dir / "baseline1" / "result.json").is_file())


if __name__ == "__main__":
    unittest.main()
