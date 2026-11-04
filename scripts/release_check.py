#!/usr/bin/env python3
"""릴리즈 전에 스킬을 검증한다.

    python3 scripts/release_check.py --free                  # 비용 없는 검사만
    python3 scripts/release_check.py --plugin common         # 비용 없는 검사 + 바뀐 스킬 평가
    python3 scripts/release_check.py --plugin common --since <ref>

바뀐 스킬은 마지막 `<플러그인>/v*` 태그(또는 --since) 이후 기준이다. 평가는 케이스마다 1회 돌리고,
실패한 케이스만 그 케이스의 기본 횟수로 다시 돌려 판정한다.

종료 코드: 통과 0, 실패 1.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
BUILD_SKILL_SCRIPTS = ROOT / "plugins" / "common" / "skills" / "build-skill" / "scripts"
LINT_SKILL = BUILD_SKILL_SCRIPTS / "lint_skill.py"
RUN_SKILL_TEST = BUILD_SKILL_SCRIPTS / "run_skill_test.py"
EVAL_ERROR = 2

sys.path.insert(0, str(BUILD_SKILL_SCRIPTS))
from _harness import discover_cases  # noqa: E402


@dataclass
class EvalPlan:
    evaluate: list[str] = field(default_factory=list)
    references_only: list[str] = field(default_factory=list)
    no_evals: list[str] = field(default_factory=list)


def unit_test_dirs(root: Path) -> list[Path]:
    candidates = [root / "scripts", *sorted((root / "plugins").glob("*/skills/*/scripts"))]
    return [path for path in candidates if any(path.glob("test_*.py"))]


def free_commands(root: Path) -> list[tuple[str, list[str]]]:
    test_dirs = unit_test_dirs(root)
    if not test_dirs:
        raise RuntimeError(f"단위 테스트 폴더를 찾지 못했다 — {root}")
    return [
        ("check_consistency", [sys.executable, str(root / "scripts" / "check_consistency.py")]),
        ("lint_skill", [sys.executable, str(LINT_SKILL), "--all", str(root / "plugins")]),
        *[
            (
                f"단위 테스트 {path.relative_to(root)}",
                [sys.executable, "-m", "unittest", "discover", "-s", str(path), "-p", "test_*.py"],
            )
            for path in test_dirs
        ],
    ]


def run_commands(root: Path, commands: list[tuple[str, list[str]]]) -> bool:
    all_ok = True
    for label, command in commands:
        done = subprocess.run(command, cwd=root, capture_output=True, text=True)
        print(f"{'통과' if done.returncode == 0 else '실패'}: {label}")
        if done.returncode != 0:
            all_ok = False
            print(done.stdout + done.stderr)
    return all_ok


def latest_tag(root: Path, plugin: str) -> str | None:
    done = subprocess.run(
        ["git", "tag", "--list", f"{plugin}/v*", "--sort=-v:refname"],
        cwd=root, capture_output=True, text=True, check=True,
    )
    tags = done.stdout.split()
    return tags[0] if tags else None


def changed_paths(root: Path, plugin: str, since: str) -> list[str]:
    done = subprocess.run(
        ["git", "diff", "--name-only", "-z", f"{since}..HEAD", "--", f"plugins/{plugin}/skills"],
        cwd=root, capture_output=True, text=True, check=True,
    )
    return [path for path in done.stdout.split("\0") if path]


def plan_evals(root: Path, plugin: str, paths: list[str]) -> EvalPlan:
    prefix = f"plugins/{plugin}/skills/"
    files_by_skill: dict[str, list[str]] = {}
    for path in paths:
        if path.count("/") < 4:
            continue
        skill, relative = path.removeprefix(prefix).split("/", 1)
        files_by_skill.setdefault(skill, []).append(relative)

    plan = EvalPlan()
    for skill, files in sorted(files_by_skill.items()):
        skill_dir = root / prefix / skill
        if not (skill_dir / "SKILL.md").is_file():
            continue
        if all(file.startswith("references/") for file in files):
            plan.references_only.append(skill)
        elif discover_cases(skill_dir):
            plan.evaluate.append(skill)
        else:
            plan.no_evals.append(skill)
    return plan


def all_skills_as_paths(root: Path, plugin: str) -> list[str]:
    skills = (root / "plugins" / plugin / "skills").glob("*/SKILL.md")
    return [str(path.relative_to(root)) for path in sorted(skills)]


def run_eval(skill_dir: Path, args: list[str]) -> tuple[int, dict]:
    with tempfile.TemporaryDirectory() as temp:
        report_path = Path(temp) / "report.json"
        done = subprocess.run(
            [sys.executable, str(RUN_SKILL_TEST), str(skill_dir), *args, "--json", str(report_path)],
        )
        report = json.loads(report_path.read_text()) if report_path.is_file() else {}
    return done.returncode, report


def failed_cases(skill_dir: Path, run: Callable[[Path, list[str]], tuple[int, dict]]) -> list[str]:
    returncode, report = run(skill_dir, ["--runs", "1"])
    if returncode == 0:
        return []
    if returncode == EVAL_ERROR or not report.get("cases"):
        return [f"{skill_dir.name}: 평가를 실행하지 못했다(종료 코드 {returncode})"]

    failing = [case["case"] for case in report["cases"] if case["pass"] != case["total"]]
    if not failing:
        return [f"{skill_dir.name}: 종료 코드 {returncode}인데 실패 케이스가 보고서에 없다"]

    still_failed = []
    for case in failing:
        print(f"재실행: {skill_dir.name}/{case}")
        retry_code, _ = run(skill_dir, ["--case", case])
        if retry_code != 0:
            still_failed.append(f"{skill_dir.name}/{case}")
    return still_failed


def run_changed_evals(root: Path, plugin: str, since: str | None) -> bool:
    if since is None:
        print(f"{plugin}: 태그가 없어 모든 스킬을 바뀐 것으로 본다")
        paths = all_skills_as_paths(root, plugin)
    else:
        print(f"{plugin}: {since} 이후 변경 기준")
        paths = changed_paths(root, plugin, since)
    plan = plan_evals(root, plugin, paths)

    failures: list[str] = []
    for skill in plan.evaluate:
        failures += failed_cases(root / "plugins" / plugin / "skills" / skill, run_eval)

    print(f"평가 실행: {', '.join(plan.evaluate) or '없음'}")
    print(f"평가 생략(references만 변경): {', '.join(plan.references_only) or '없음'}")
    print(f"평가 없음: {', '.join(plan.no_evals) or '없음'}")
    print(f"평가 실패: {', '.join(failures) or '없음'}")
    return not failures


def main() -> int:
    parser = argparse.ArgumentParser(description="릴리즈 전 스킬 검증")
    parser.add_argument("--free", action="store_true", help="비용 없는 검사만 실행")
    parser.add_argument("--plugin", help="바뀐 스킬을 평가할 플러그인")
    parser.add_argument("--since", help="변경 기준 ref (기본: 마지막 태그)")
    args = parser.parse_args()
    if args.free == bool(args.plugin):
        parser.error("--free와 --plugin 중 하나만 쓴다")
    if args.since and not args.plugin:
        parser.error("--since는 --plugin과 함께 쓴다")

    if not run_commands(ROOT, free_commands(ROOT)):
        return 1
    if args.free:
        return 0
    since = args.since or latest_tag(ROOT, args.plugin)
    return 0 if run_changed_evals(ROOT, args.plugin, since) else 1


if __name__ == "__main__":
    sys.exit(main())
