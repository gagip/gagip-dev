#!/usr/bin/env python3
"""스킬의 결정론적 테스트를 실행한다.

    python3 run_skill_test.py <스킬디렉토리> [옵션]
    python3 run_skill_test.py --all [<스캔루트>]   # 루트 아래 모든 스킬 (기본 루트: cwd)

<스킬디렉토리>/evals/*.py 각 케이스를 격리 환경에서 `claude -p`로 실행하고,
케이스 파일의 check(ctx)로 결과를 검증한다. check는 코드다. 케이스마다 PASS / FAIL / REVIEW를
판정하고 근거 한 줄과 비용(시간·토큰·턴)을 함께 낸다(판정 규칙은 _verdict.judge).
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

종료 코드: FAIL 케이스가 있으면 1, 없으면 0(REVIEW만 있어도 0). 인자 오류는 2.
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import (  # noqa: E402
    Case, CaseResult, RunCost, RunResult, applies_to_model, discover_cases, discover_skills,
    load_case, run_case, sum_costs, unused_bundle_files,
)
from _artifacts import find_runs_root, save_case  # noqa: E402
from _llm_grade import Grade, grade_run, summarize  # noqa: E402
from _verdict import Judgement, Verdict, judge  # noqa: E402


@dataclass
class Outcome:
    """케이스 하나의 실행 결과와 판정. grades[i]는 i번째 run의 LLM 채점(채점 안 했으면 None)."""
    case: Case
    result: CaseResult
    judgement: Judgement
    grades: list[Grade | None] = field(default_factory=list)

    def grade_cost(self) -> RunCost | None:
        return sum_costs(g.cost for g in self.grades if g is not None)


def total_cost(runs: list[RunResult]) -> RunCost | None:
    return sum_costs(r.cost for r in runs)


def fmt_cost(cost: RunCost | None) -> str:
    if cost is None:
        return "비용 모름"
    return (f"{cost.duration_ms / 1000:.1f}s · 입력 {cost.input_tokens:,}(+캐시 {cost.cache_tokens:,})"
            f" / 출력 {cost.output_tokens:,} 토큰"
            f" · 턴 {cost.turns} · ${cost.usd:.3f}")


def _fmt(o: Outcome) -> str:
    cr, j = o.result, o.judgement
    line = f"  {cr.case:<24} {cr.pass_count}/{len(cr.runs)} {j.verdict.value:<6} {j.reason}"
    if cr.baseline:
        line += f"   (baseline {cr.baseline_pass_count}/{len(cr.baseline)})"
    line += f"\n      비용: {fmt_cost(total_cost(cr.runs))}"
    if o.grades:
        line += f"\n      채점 비용: {fmt_cost(o.grade_cost())}"
    for i, g in enumerate(o.grades, 1):
        if g is None:
            continue
        for item in g.items:
            if not item.passed:
                line += f"\n      run{i} LLM #{item.no} 미통과: \"{item.quote[:160]}\""
                if item.fix:
                    line += f"\n        고칠 문장: {item.fix[:160]}"
    if j.verdict is not Verdict.PASS and o.case.review_focus:
        line += f"\n      볼 것: {o.case.review_focus}"
    fails = [r for r in cr.runs if not r.passed]
    for r in fails[:3]:
        line += f"\n      - {r.reason}"
    return line


_MATRIX_MARK = {"PASS": "", "REVIEW": " △", "FAIL": " ✗"}


def matrix_markdown(skill_reports: list[dict], models: list[str]) -> str:
    """스킬별로 케이스 × 모델 pass/total 표를 마크다운으로 만든다."""
    by_skill: dict[str, dict[str, dict[str, str]]] = {}
    for rep in skill_reports:
        model = rep.get("model") or "(기본)"
        for c in rep["cases"]:
            cell = f"{c['pass']}/{c['total']}" + _MATRIX_MARK[c["verdict"]]
            by_skill.setdefault(rep["skill"], {}).setdefault(c["case"], {})[model] = cell
    lines: list[str] = []
    for skill, cases in by_skill.items():
        lines += [f"### {Path(skill).name}", "",
                  "| 케이스 | " + " | ".join(models) + " |",
                  "|---|" + "---|" * len(models)]
        for case, cells in cases.items():
            lines.append(f"| {case} | " + " | ".join(cells.get(m, "-") for m in models) + " |")
        lines.append("")
    return "\n".join(lines)


def _cost_json(cost: RunCost | None) -> dict | None:
    return None if cost is None else {**asdict(cost), "tokens": cost.tokens}


def _run_json(r: RunResult, *, files_read: bool, grade: Grade | None = None) -> dict:
    out = {"passed": r.passed, "reason": r.reason, "error": r.error, "skill_fired": r.skill_fired,
           "tools": r.tool_names, "final_text": r.final_text, "cost": _cost_json(r.cost)}
    if files_read:
        out["files_read"] = r.files_read
    if grade is not None:
        out["llm"] = grade.to_json()
    return out


def _grade_at(o: Outcome, i: int) -> Grade | None:
    return o.grades[i] if i < len(o.grades) else None


def _skill_payload(skill_dir: Path, outcomes: list[Outcome]) -> dict:
    # pass·total·all_ok 키는 release_check와 CI artifact를 읽는 쪽이 쓰므로 뜻을 유지한다(all_ok = FAIL 없음).
    results = [o.result for o in outcomes]
    return {
        "skill": str(skill_dir),
        "model": results[0].model if results else None,
        "all_ok": all(o.judgement.verdict is not Verdict.FAIL for o in outcomes),
        "unused_files": unused_bundle_files(skill_dir, results),
        "cases": [
            {
                "case": o.result.case,
                "verdict": o.judgement.verdict.value,
                "reason": o.judgement.reason,
                "grader": o.case.grader,
                "review_focus": o.case.review_focus,
                "pass": o.result.pass_count,
                "total": len(o.result.runs),
                "baseline_pass": o.result.baseline_pass_count,
                "baseline_total": len(o.result.baseline),
                "cost": _cost_json(total_cost(o.result.runs)),
                "grade_cost": _cost_json(o.grade_cost()),
                "runs": [_run_json(r, files_read=True, grade=_grade_at(o, i))
                         for i, r in enumerate(o.result.runs)],
                "baseline_runs": [_run_json(r, files_read=False) for r in o.result.baseline],
            }
            for o in outcomes
        ],
    }


def _run_skill(skill_dir: Path, args) -> list[Outcome] | None:
    """한 스킬의 케이스를 모두 실행. 케이스가 없으면 None."""
    case_paths = discover_cases(skill_dir)
    if args.case:
        case_paths = [p for p in case_paths if p.stem == args.case]
    if not case_paths:
        return None

    outcomes: list[Outcome] = []
    for cp in case_paths:
        case = load_case(cp)
        if not applies_to_model(case, args.model):
            print(f"▷ {skill_dir.name}/{case.name}  건너뜀 (MODELS={case.models}, 모델={args.model})",
                  file=sys.stderr)
            continue
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
        try:
            grades, summary = _grade_case(skill_dir, case, cr, args)
            outcome = Outcome(case, cr, judge(case, cr, args.threshold, llm_summary=summary), grades)
            outcomes.append(outcome)
            print(_fmt(outcome), file=sys.stderr)
            if outcome.judgement.verdict is not Verdict.PASS:
                extras = [None if g is None else {"llm": g.to_json()} for g in grades] if grades else None
                saved = save_case(args.run_root, skill_dir.name, cr, _case_record(outcome), extras)
                print(f"      산출물: {saved}", file=sys.stderr)
        finally:
            if not args.keep_temp:
                cr.discard()
    return outcomes


def _grade_case(skill_dir: Path, case: Case, cr: CaseResult, args) -> tuple[list[Grade | None], str | None]:
    """GRADER="llm"이면 구조 검사를 통과한 run을 채점한다. (run별 채점, 요약 한 줄)."""
    if case.grader != "llm":
        return [], None
    if args.no_llm_grade:
        return [], "LLM 채점 꺼짐(--no-llm-grade)"
    grades = [
        grade_run(r, skill_dir=skill_dir, request=case.prompt, model=args.grader_model, timeout=args.timeout)
        if r.passed and not r.error else None
        for r in cr.runs
    ]
    return grades, summarize(grades)


def _case_record(o: Outcome) -> dict:
    return {"case": o.result.case, "model": o.result.model, "verdict": o.judgement.verdict.value,
            "reason": o.judgement.reason, "grader": o.case.grader, "review_focus": o.case.review_focus,
            "pass": o.result.pass_count, "total": len(o.result.runs),
            "cost": _cost_json(total_cost(o.result.runs)), "grade_cost": _cost_json(o.grade_cost())}


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
    ap.add_argument("--models",
                    help="쉼표로 구분한 모델 목록(예: haiku,sonnet,opus). 모델마다 전체를 돌려 "
                         "케이스 × 모델 표를 낸다. 호출이 모델 수만큼 늘어나므로 주간 CI처럼 가끔만 쓴다")
    ap.add_argument("--matrix-md", type=Path,
                    help="--models 결과 표를 마크다운 파일로 저장 (CI 요약용)")
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--timeout", type=int, default=300, help="run 당 초 (기본 300)")
    ap.add_argument("--threshold", type=float, default=1.0,
                    help="이 비율보다 적게 통과하면 FAIL (기본 1.0 = 전 run 통과). 넘었지만 일부 run이 "
                         "실패하면 REVIEW")
    ap.add_argument("--keep-temp", action="store_true", help="임시 디렉토리 보존 (디버깅)")
    ap.add_argument("--grader-model", default="sonnet",
                    help='GRADER="llm" 케이스를 채점할 모델 (기본 sonnet)')
    ap.add_argument("--no-llm-grade", action="store_true",
                    help="LLM 채점을 건너뛴다(그 케이스는 REVIEW로 남는다). 모델 매트릭스·재실행용")
    ap.add_argument("--runs-dir", type=Path,
                    help="REVIEW·FAIL 산출물을 둘 곳 (기본: 스킬이 든 레포 루트의 .eval-runs)")
    ap.add_argument("--json", dest="json_out", nargs="?", const="-",
                    help="전체 결과를 JSON으로 (경로 없으면 stdout)")
    args = ap.parse_args()
    if not 0.0 <= args.threshold <= 1.0:
        print("오류: --threshold는 0~1 사이다", file=sys.stderr)
        return 2

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

    for skill_dir in skill_dirs:
        if not (skill_dir / "SKILL.md").is_file():
            print(f"오류: SKILL.md가 없다 — {skill_dir}", file=sys.stderr)
            return 2

    runs_dir = args.runs_dir or find_runs_root(skill_dirs[0])
    args.run_root = runs_dir / datetime.now().strftime("%Y-%m-%d_%H%M%S")

    models: list[str | None] = [m.strip() for m in args.models.split(",") if m.strip()] \
        if args.models else [args.model]
    if args.matrix_md and not args.models:
        print("오류: --matrix-md는 --models와 함께 쓴다", file=sys.stderr)
        return 2

    skill_reports: list[dict] = []
    missing: list[Path] = []
    skipped_all = False
    for model in models:
        args.model = model
        if args.models:
            print(f"\n=== 모델: {model} ===", file=sys.stderr)
        for skill_dir in skill_dirs:
            results = _run_skill(skill_dir, args)
            if results is None:
                missing.append(skill_dir)
                continue
            if not results:
                skipped_all = True
                continue
            report = _skill_payload(skill_dir, results)
            skill_reports.append(report)
            if report["unused_files"]:
                print("  참고: 이 평가에서 한 번도 열리지 않은 번들 파일 — "
                      + ", ".join(report["unused_files"]), file=sys.stderr)

    if not skill_reports and skipped_all:
        print("오류: 선택한 모델이 모든 케이스의 MODELS에서 제외돼 실행할 케이스가 없다", file=sys.stderr)
        return 2
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

    if args.models:
        table = matrix_markdown(skill_reports, [m for m in models if m])
        print("\n" + table, file=sys.stderr)
        if args.matrix_md:
            args.matrix_md.write_text(table, encoding="utf-8")
            print(f"표 저장: {args.matrix_md}", file=sys.stderr)
    elif len(skill_reports) > 1:
        for s in skill_reports:
            print(f"  {'✓' if s['all_ok'] else '✗'} {s['skill']}", file=sys.stderr)
    counts = {v: sum(c["verdict"] == v.value for s in skill_reports for c in s["cases"]) for v in Verdict}
    print(f"\nPASS {counts[Verdict.PASS]} · REVIEW {counts[Verdict.REVIEW]} · FAIL {counts[Verdict.FAIL]}"
          f" — {'FAIL 없음' if all_ok else 'FAIL 케이스 있음'}", file=sys.stderr)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
