#!/usr/bin/env python3
"""스킬의 결정론적 테스트를 실행한다.

    python3 run_skill_test.py <스킬디렉토리> [옵션]
    python3 run_skill_test.py --all [<스캔루트>]   # 루트 아래 모든 스킬 (기본 루트: cwd)

<스킬디렉토리>/evals/*.py 각 케이스를 격리 환경에서 `claude -p`로 실행하고,
케이스 파일의 check(ctx)로 결과를 검증한다. check는 100% 코드 — LLM 심판 없음.
`--all`은 SKILL.md와 실행 가능한 evals/*.py를 함께 가진 디렉터리를 모두 찾아 순회한다
(CI 주간 실행용). `--json`은 이때 {"all_ok", "skills": [...]} 형태로 나온다.

케이스 파일 형식 (evals/basic.py):

    PROMPT = "커밋해줘"
    RUNS = 3                       # 선택, 기본 3
    SCAFFOLD = "git init -q; ..."  # 선택, 각 run 전 임시 디렉토리에서 실행
    PERMISSION_MODE = "acceptEdits"  # 선택

    def check(ctx):
        assert ctx.re_match(ctx.git_log_subject(), r"^(feat|fix|chore): .+")
        assert not ctx.bash_ran(r"git\\s+push")
        assert ctx.skill_fired()

ctx 헬퍼는 _harness.py의 Ctx 참조.

종료 코드: 전 케이스가 임계값(--threshold, 기본 1.0) 이상 통과하면 0, 아니면 1.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import (  # noqa: E402
    CaseResult, discover_cases, discover_skills, load_case, run_case,
)


def _fmt(cr: CaseResult, threshold: float) -> str:
    total = len(cr.runs)
    mark = "PASS" if cr.ok(threshold) else "FAIL"
    line = f"  {cr.case:<24} {cr.pass_count}/{total} {mark}"
    if cr.baseline:
        line += f"   (baseline {cr.baseline_pass_count}/{len(cr.baseline)})"
    fails = [r for r in cr.runs if not r.passed]
    for i, r in enumerate(fails[:3]):
        line += f"\n      - {r.reason}"
    return line


def _skill_payload(skill_dir: Path, results: list[CaseResult], threshold: float) -> dict:
    return {
        "skill": str(skill_dir),
        "all_ok": all(cr.ok(threshold) for cr in results),
        "cases": [
            {
                "case": cr.case,
                "pass": cr.pass_count,
                "total": len(cr.runs),
                "baseline_pass": cr.baseline_pass_count,
                "baseline_total": len(cr.baseline),
                "runs": [
                    {"passed": r.passed, "reason": r.reason, "error": r.error,
                     "tools": r.tool_names, "final_text": r.final_text}
                    for r in cr.runs
                ],
                "baseline_runs": [
                    {"passed": r.passed, "reason": r.reason, "error": r.error,
                     "tools": r.tool_names, "final_text": r.final_text}
                    for r in cr.baseline
                ],
            }
            for cr in results
        ],
    }


def _run_skill(skill_dir: Path, args) -> list[CaseResult] | None:
    """한 스킬의 케이스를 모두 실행. 케이스가 없으면 None."""
    case_paths = discover_cases(skill_dir)
    if args.case:
        case_paths = [p for p in case_paths if p.stem == args.case]
    if not case_paths:
        return None

    results: list[CaseResult] = []
    for cp in case_paths:
        case = load_case(cp)
        if args.runs:
            case.runs = args.runs
        print(f"▶ {skill_dir.name}/{case.name}  "
              f"(runs={case.runs}{', +baseline' if args.baseline else ''})",
              file=sys.stderr)
        cr = run_case(
            skill_dir, case,
            baseline=args.baseline, model=args.model,
            max_turns=args.max_turns, timeout=args.timeout, keep_temp=args.keep_temp,
        )
        results.append(cr)
        print(_fmt(cr, args.threshold), file=sys.stderr)
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="스킬 결정론적 테스트 러너")
    ap.add_argument("skill_dir", type=Path, nargs="?",
                    help="테스트할 스킬 디렉토리 (SKILL.md 포함). --all이면 스캔 루트 (기본: cwd)")
    ap.add_argument("--all", action="store_true",
                    help="루트 아래 SKILL.md + evals/*.py를 가진 모든 스킬을 실행")
    ap.add_argument("--case", help="특정 케이스만 (evals/<이름>.py 의 <이름>)")
    ap.add_argument("--baseline", action="store_true",
                    help="스킬 없이 동일 프롬프트도 1회 실행해 대조 (신규 스킬 평가용)")
    ap.add_argument("--runs", type=int, help="케이스의 RUNS를 덮어씀 (개발 중 1 권장)")
    ap.add_argument("--model", help="claude -p 모델 (기본: 사용자 설정). 현재 세션과 맞추려면 지정")
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--timeout", type=int, default=300, help="run 당 초 (기본 300)")
    ap.add_argument("--threshold", type=float, default=1.0,
                    help="케이스 통과 판정 비율 (기본 1.0 = 전 run 통과)")
    ap.add_argument("--keep-temp", action="store_true", help="임시 디렉토리 보존 (디버깅)")
    ap.add_argument("--json", dest="json_out", nargs="?", const="-",
                    help="전체 결과를 JSON으로 (경로 없으면 stdout)")
    args = ap.parse_args()

    if args.all:
        root = (args.skill_dir or Path.cwd()).resolve()
        skill_dirs = discover_skills(root)
        if not skill_dirs:
            print(f"오류: evals를 가진 스킬이 없다 — {root}", file=sys.stderr)
            return 2
    else:
        if args.skill_dir is None:
            print("오류: 스킬 디렉토리를 지정하거나 --all을 쓴다", file=sys.stderr)
            return 2
        skill_dirs = [args.skill_dir]

    skill_reports: list[dict] = []
    missing: list[Path] = []
    for skill_dir in skill_dirs:
        if not (skill_dir / "SKILL.md").is_file():
            print(f"오류: SKILL.md가 없다 — {skill_dir}", file=sys.stderr)
            return 2
        results = _run_skill(skill_dir, args)
        if results is None:
            missing.append(skill_dir)
            continue
        skill_reports.append(_skill_payload(skill_dir, results, args.threshold))

    if not skill_reports:
        where = f"evals/{args.case}.py" if args.case else "evals/*.py"
        joined = ", ".join(str(p) for p in missing) or str(skill_dirs)
        print(f"오류: 케이스가 없다 — {joined}/{where}", file=sys.stderr)
        return 2

    all_ok = all(s["all_ok"] for s in skill_reports)

    if args.json_out:
        if args.all or len(skill_reports) > 1:
            payload: dict = {"all_ok": all_ok, "skills": skill_reports}
        else:
            payload = skill_reports[0]
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.json_out == "-":
            print(text)
        else:
            Path(args.json_out).write_text(text)
            print(f"JSON 저장: {args.json_out}", file=sys.stderr)

    if len(skill_reports) > 1:
        for s in skill_reports:
            print(f"  {'✓' if s['all_ok'] else '✗'} {s['skill']}", file=sys.stderr)
    print(f"\n{'전체 통과' if all_ok else '실패 케이스 있음'}", file=sys.stderr)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
