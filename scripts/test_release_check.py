from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import release_check


def write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def make_skill(root: Path, name: str, evals: bool) -> None:
    skill_dir = root / "plugins" / "common" / "skills" / name
    write(skill_dir / "SKILL.md")
    if evals:
        write(skill_dir / "evals" / "case.py")


class PlanEvalsTest(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def plan(self, *paths: str) -> release_check.EvalPlan:
        return release_check.plan_evals(self.root, "common", list(paths))

    def test_references_only_change_skips_eval(self) -> None:
        make_skill(self.root, "alpha", evals=True)

        plan = self.plan("plugins/common/skills/alpha/references/a.md")

        self.assertEqual(plan.references_only, ["alpha"])
        self.assertEqual(plan.evaluate, [])

    def test_skill_md_or_script_change_runs_eval(self) -> None:
        make_skill(self.root, "alpha", evals=True)
        make_skill(self.root, "beta", evals=True)

        plan = self.plan(
            "plugins/common/skills/alpha/SKILL.md",
            "plugins/common/skills/beta/scripts/tool.py",
        )

        self.assertEqual(plan.evaluate, ["alpha", "beta"])

    def test_references_with_skill_md_runs_eval(self) -> None:
        make_skill(self.root, "alpha", evals=True)

        plan = self.plan(
            "plugins/common/skills/alpha/references/a.md",
            "plugins/common/skills/alpha/SKILL.md",
        )

        self.assertEqual(plan.evaluate, ["alpha"])
        self.assertEqual(plan.references_only, [])

    def test_skill_without_evals_is_listed_not_evaluated(self) -> None:
        make_skill(self.root, "alpha", evals=False)

        plan = self.plan("plugins/common/skills/alpha/SKILL.md")

        self.assertEqual(plan.no_evals, ["alpha"])
        self.assertEqual(plan.evaluate, [])

    def test_deleted_skill_is_ignored(self) -> None:
        plan = self.plan("plugins/common/skills/gone/SKILL.md")

        self.assertEqual(plan, release_check.EvalPlan())


    def test_other_plugin_and_plugin_level_files_are_ignored(self) -> None:
        make_skill(self.root, "alpha", evals=True)

        plan = self.plan(
            "plugins/other/skills/alpha/SKILL.md",
            "plugins/common/skills/README.md",
        )

        self.assertEqual(plan, release_check.EvalPlan())

    def test_without_tag_every_skill_counts_as_changed(self) -> None:
        make_skill(self.root, "alpha", evals=True)
        make_skill(self.root, "beta", evals=False)

        paths = release_check.all_skills_as_paths(self.root, "common")
        plan = release_check.plan_evals(self.root, "common", paths)

        self.assertEqual(plan.evaluate, ["alpha"])
        self.assertEqual(plan.no_evals, ["beta"])


class FailedCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.calls: list[list[str]] = []

    def fake_run(self, first: tuple[int, dict], retry_codes: dict[str, int]):
        def run(_skill_dir: Path, args: list[str]) -> tuple[int, dict]:
            self.calls.append(args)
            if "--case" in args:
                return retry_codes[args[args.index("--case") + 1]], {}
            return first
        return run

    def test_first_pass_needs_no_retry(self) -> None:
        failed = release_check.failed_cases(Path("alpha"), self.fake_run((0, {}), {}))

        self.assertEqual(failed, [])
        self.assertEqual(self.calls, [["--runs", "1"]])

    def test_retries_only_failed_case_and_passes_when_retry_passes(self) -> None:
        report = {"cases": [
            {"case": "good", "pass": 1, "total": 1},
            {"case": "flaky", "pass": 0, "total": 1},
        ]}

        failed = release_check.failed_cases(Path("alpha"), self.fake_run((1, report), {"flaky": 0}))

        self.assertEqual(failed, [])
        self.assertEqual(self.calls, [["--runs", "1"], ["--case", "flaky"]])

    def test_failed_retry_is_reported(self) -> None:
        report = {"cases": [{"case": "broken", "pass": 0, "total": 1}]}

        failed = release_check.failed_cases(Path("alpha"), self.fake_run((1, report), {"broken": 1}))

        self.assertEqual(failed, ["alpha/broken"])

    def test_runner_error_fails_without_retry(self) -> None:
        failed = release_check.failed_cases(Path("alpha"), self.fake_run((2, {}), {}))

        self.assertEqual(len(failed), 1)
        self.assertEqual(self.calls, [["--runs", "1"]])


    def test_failure_exit_without_failed_case_is_a_failure(self) -> None:
        report = {"cases": [{"case": "empty", "pass": 0, "total": 0}]}

        failed = release_check.failed_cases(Path("alpha"), self.fake_run((1, report), {}))

        self.assertEqual(len(failed), 1)
        self.assertEqual(self.calls, [["--runs", "1"]])


class FreeChecksTest(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_every_skill_with_tests_is_collected(self) -> None:
        write(self.root / "plugins/common/skills/alpha/scripts/test_a.py")
        write(self.root / "plugins/common/skills/beta/scripts/tool.py")
        write(self.root / "scripts/test_b.py")

        dirs = release_check.unit_test_dirs(self.root)

        self.assertEqual(dirs, [
            self.root / "scripts",
            self.root / "plugins/common/skills/alpha/scripts",
        ])

    def test_no_test_dirs_is_an_error(self) -> None:
        with self.assertRaises(RuntimeError):
            release_check.free_commands(self.root)

    def test_failing_command_fails_and_later_commands_still_run(self) -> None:
        marker = self.root / "ran"
        commands = [
            ("fail", [sys.executable, "-c", "raise SystemExit(1)"]),
            ("mark", [sys.executable, "-c", f"open({str(marker)!r}, 'w')"]),
        ]

        self.assertFalse(release_check.run_commands(self.root, commands))
        self.assertTrue(marker.exists())

    def test_passing_commands_pass(self) -> None:
        commands = [("ok", [sys.executable, "-c", "pass"])]

        self.assertTrue(release_check.run_commands(self.root, commands))


class GitLookupTest(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.git("init", "-q")

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=self.root, check=True, capture_output=True,
        )

    def commit(self, relative: str) -> None:
        write(self.root / relative)
        self.git("add", "-A")
        self.git("commit", "-qm", "c")

    def test_latest_tag_compares_versions_numerically(self) -> None:
        self.commit("a")
        for tag in ("common/v0.9.0", "common/v0.60.3", "other/v9.0.0"):
            self.git("tag", tag)

        self.assertEqual(release_check.latest_tag(self.root, "common"), "common/v0.60.3")

    def test_latest_tag_is_none_without_tags(self) -> None:
        self.commit("a")

        self.assertIsNone(release_check.latest_tag(self.root, "common"))

    def test_changed_paths_are_limited_to_plugin_skills_since_ref(self) -> None:
        self.commit("plugins/common/skills/old/SKILL.md")
        self.git("tag", "common/v1.0.0")
        self.commit("plugins/common/skills/한글/SKILL.md")
        self.commit("plugins/common/CHANGELOG.md")

        paths = release_check.changed_paths(self.root, "common", "common/v1.0.0")

        self.assertEqual(paths, ["plugins/common/skills/한글/SKILL.md"])


if __name__ == "__main__":
    unittest.main()
