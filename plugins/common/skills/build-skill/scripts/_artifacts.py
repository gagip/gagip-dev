"""REVIEW·FAIL 케이스의 산출물을 `.eval-runs/`에 남긴다.

    .eval-runs/<날짜시각>/<스킬>/<케이스>[@모델]/
        case.json                 판정·근거·볼 것·비용
        run<n>/result.json        run 기록(통과 여부·사유·도구·비용, LLM 채점이 있으면 그 결과)
        run<n>/final.md           마지막 응답
        run<n>/files/<경로>       scaffold 뒤 새로 생기거나 바뀐 파일
        baseline<n>/...           baseline run도 같은 모양
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path

from _harness import CaseResult, RunResult

RUNS_DIR_NAME = ".eval-runs"


def find_runs_root(start: Path) -> Path:
    """start에서 위로 올라가며 .git을 찾아 `<레포 루트>/.eval-runs`를 돌려준다. 못 찾으면 cwd 기준."""
    start = start.resolve()
    for d in (start, *start.parents):
        if (d / ".git").exists():
            return d / RUNS_DIR_NAME
    return Path.cwd() / RUNS_DIR_NAME


def _run_record(r: RunResult, extra: dict | None) -> dict:
    return {
        "passed": r.passed, "reason": r.reason, "error": r.error, "skill_fired": r.skill_fired,
        "tools": r.tool_names, "bash_cmds": r.bash_cmds, "files_read": r.files_read,
        "cost": None if r.cost is None else asdict(r.cost),
        "changed_files": r.changed_files(),
        **(extra or {}),
    }


def _save_run(dest: Path, r: RunResult, extra: dict | None) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "result.json").write_text(
        json.dumps(_run_record(r, extra), ensure_ascii=False, indent=2), encoding="utf-8")
    (dest / "final.md").write_text(r.final_text, encoding="utf-8")
    if r.workdir is None:
        return
    for rel in r.changed_files():
        target = dest / "files" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(r.workdir / rel, target)


def save_case(run_root: Path, skill: str, result: CaseResult, case_record: dict,
              run_extras: list[dict | None] | None = None) -> Path:
    """케이스 하나의 run을 모두 복사하고 케이스 폴더 경로를 돌려준다.

    run_extras[i]는 i번째 run의 result.json에 더할 값(예: LLM 채점 결과)이다.
    """
    name = result.case + (f"@{result.model}" if result.model else "")
    case_dir = run_root / skill / name
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "case.json").write_text(json.dumps(case_record, ensure_ascii=False, indent=2), encoding="utf-8")
    extras = run_extras or [None] * len(result.runs)
    assert len(extras) == len(result.runs), "run_extras 길이가 run 수와 다르다"
    for i, (r, extra) in enumerate(zip(result.runs, extras), 1):
        _save_run(case_dir / f"run{i}", r, extra)
    for i, r in enumerate(result.baseline, 1):
        _save_run(case_dir / f"baseline{i}", r, None)
    return case_dir
