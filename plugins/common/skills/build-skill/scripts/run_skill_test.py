#!/usr/bin/env python3
"""스킬의 결정론적 테스트를 실행한다.

    python3 run_skill_test.py <스킬디렉토리> [옵션]

<스킬디렉토리>/evals/*.py 각 케이스를 격리 환경에서 `claude -p`로 실행하고,
케이스 파일의 check(ctx)로 결과를 검증한다. check는 100% 코드 — LLM 심판 없음.

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
    CaseResult, discover_cases, load_case, run_case,
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


def main() -> int:
    ap = argparse.ArgumentParser(description="스킬 결정론적 테스트 러너")
    ap.add_argument("skill_dir", type=Path, help="테스트할 스킬 디렉토리 (SKILL.md 포함)")
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

    skill_dir: Path = args.skill_dir
    if not (skill_dir / "SKILL.md").is_file():
        print(f"오류: SKILL.md가 없다 — {skill_dir}", file=sys.stderr)
        return 2

    case_paths = discover_cases(skill_dir)
    if args.case:
        case_paths = [p for p in case_paths if p.stem == args.case]
    if not case_paths:
        where = f"evals/{args.case}.py" if args.case else "evals/*.py"
        print(f"오류: 케이스가 없다 — {skill_dir}/{where}", file=sys.stderr)
        return 2

    results: list[CaseResult] = []
    for cp in case_paths:
        case = load_case(cp)
        if args.runs:
            case.runs = args.runs
        print(f"▶ {case.name}  (runs={case.runs}{', +baseline' if args.baseline else ''})",
              file=sys.stderr)
        cr = run_case(
            skill_dir, case,
            baseline=args.baseline, model=args.model,
            max_turns=args.max_turns, timeout=args.timeout, keep_temp=args.keep_temp,
        )
        results.append(cr)
        print(_fmt(cr, args.threshold), file=sys.stderr)

    all_ok = all(cr.ok(args.threshold) for cr in results)

    if args.json_out:
        payload = {
            "skill": str(skill_dir),
            "all_ok": all_ok,
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
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.json_out == "-":
            print(text)
        else:
            Path(args.json_out).write_text(text)
            print(f"JSON 저장: {args.json_out}", file=sys.stderr)

    print(f"\n{'전체 통과' if all_ok else '실패 케이스 있음'}", file=sys.stderr)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
