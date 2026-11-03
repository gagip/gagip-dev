"""러너의 관찰 헬퍼와 모델 매트릭스 표를 LLM 호출 없이 합성 이벤트로 확인한다."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import _harness
import run_skill_test


def make_ctx(*calls):
    """calls = (툴 이름, 입력 dict) 들로 assistant 이벤트를 만들어 Ctx를 얻는다."""
    content = [{"type": "tool_use", "name": n, "input": i} for n, i in calls]
    events = [{"type": "assistant", "message": {"content": content}}]
    return _harness.Ctx.build(Path("."), events, loader=None)


def run_result(files_read=(), bash_cmds=()):
    return _harness.RunResult(True, files_read=list(files_read), bash_cmds=list(bash_cmds))


class FilesReadTests(unittest.TestCase):
    def test_lists_read_paths_with_forward_slashes_and_no_duplicates(self):
        ctx = make_ctx(
            ("Read", {"file_path": "C:\\skill\\references\\a.md"}),
            ("Read", {"file_path": "C:\\skill\\references\\a.md"}),
            ("Bash", {"command": "cat references/b.md"}),
            ("Read", {"file_path": "/skill/SKILL.md"}),
        )
        self.assertEqual(["C:/skill/references/a.md", "/skill/SKILL.md"], ctx.files_read())

    def test_pattern_filters(self):
        ctx = make_ctx(("Read", {"file_path": "/s/references/a.md"}), ("Read", {"file_path": "/s/SKILL.md"}))
        self.assertEqual(["/s/references/a.md"], ctx.files_read(r"references/"))
        self.assertEqual([], ctx.files_read(r"assets/"))

    def test_no_reads(self):
        self.assertEqual([], make_ctx(("Bash", {"command": "ls"})).files_read())


class UnusedBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.skill = Path(self.tmp.name) / "demo"
        for rel in ("references/a.md", "references/b.md", "assets/t.md", "scripts/run.py",
                    "scripts/test_run.py", "scripts/_private.py"):
            path = self.skill / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x", encoding="utf-8")

    def unused(self, *runs):
        return _harness.unused_bundle_files(
            self.skill, [_harness.CaseResult("c", list(runs))])

    def test_everything_unused_when_nothing_touched(self):
        self.assertEqual(
            {"references/a.md", "references/b.md", "assets/t.md", "scripts/run.py"},
            set(self.unused(run_result())))

    def test_read_marks_used(self):
        unused = self.unused(run_result(files_read=[f"{self.skill.as_posix()}/references/a.md"]))
        self.assertNotIn("references/a.md", unused)
        self.assertIn("references/b.md", unused)

    def test_bash_mention_marks_used(self):
        unused = self.unused(run_result(bash_cmds=["python3 scripts/run.py --all"]))
        self.assertNotIn("scripts/run.py", unused)

    def test_usage_in_any_run_counts(self):
        unused = self.unused(run_result(), run_result(files_read=["/x/assets/t.md"]))
        self.assertNotIn("assets/t.md", unused)

    def test_test_and_private_files_are_never_listed(self):
        unused = self.unused(run_result())
        self.assertNotIn("scripts/test_run.py", unused)
        self.assertNotIn("scripts/_private.py", unused)

    def test_baseline_runs_are_ignored(self):
        cr = _harness.CaseResult("c", [run_result()], baseline=[run_result(files_read=["/x/assets/t.md"])])
        self.assertIn("assets/t.md", _harness.unused_bundle_files(self.skill, [cr]))


class ModelsDeclarationTests(unittest.TestCase):
    def load(self, extra_lines):
        """PROMPT·check만 있는 케이스 파일에 extra_lines를 덧붙여 불러온다."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.py"
            lines = ['PROMPT = "p"', *extra_lines, "def check(ctx):", "    pass", ""]
            path.write_text("\n".join(lines), encoding="utf-8")
            return _harness.load_case(path)

    def test_no_declaration_applies_to_every_model(self):
        case = self.load([])
        self.assertIsNone(case.models)
        for model in (None, "haiku", "opus"):
            self.assertTrue(_harness.applies_to_model(case, model))

    def test_declared_models_exclude_others(self):
        case = self.load(['MODELS = ["sonnet", "opus"]'])
        self.assertEqual(["sonnet", "opus"], case.models)
        self.assertTrue(_harness.applies_to_model(case, "opus"))
        self.assertFalse(_harness.applies_to_model(case, "haiku"))

    def test_unspecified_model_always_runs(self):
        case = self.load(['MODELS = ["sonnet"]'])
        self.assertTrue(_harness.applies_to_model(case, None))


class MatrixTests(unittest.TestCase):
    def test_table_has_a_column_per_model_and_marks_failures(self):
        def rep(model, passed):
            return {"skill": "/p/skills/demo", "model": model,
                    "cases": [{"case": "fires", "pass": passed, "total": 3}]}

        table = run_skill_test.matrix_markdown(
            [rep("haiku", 2), rep("sonnet", 3)], ["haiku", "sonnet"])
        self.assertIn("### demo", table)
        self.assertIn("| 케이스 | haiku | sonnet |", table)
        self.assertIn("| fires | 2/3 ✗ | 3/3 |", table)

    def test_missing_cell_is_dash(self):
        rep = {"skill": "/p/demo", "model": "haiku", "cases": [{"case": "c", "pass": 1, "total": 1}]}
        self.assertIn("| c | 1/1 | - |", run_skill_test.matrix_markdown([rep], ["haiku", "opus"]))


class RunFailureTests(unittest.TestCase):
    def test_timeout_reason_survives_long_prompt(self):
        class Loader:
            def claude_args(self, with_skill):
                return []

        def time_out(prompt, *args, **kwargs):
            raise subprocess.TimeoutExpired(["claude", "-p", prompt], kwargs["timeout"])

        case = _harness.Case("c", Path("c.py"), "긴 프롬프트 " * 100, 1, "", "bypassPermissions", lambda ctx: None)
        with mock.patch.object(_harness, "run_claude", time_out):
            result = _harness._one_run(case, Loader(), with_skill=True, model=None,
                                       max_turns=1, timeout=300, keep_temp=False)
        self.assertTrue(result.error)
        self.assertIn("시간 초과 300초", result.reason)


if __name__ == "__main__":
    unittest.main()
