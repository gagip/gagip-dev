#!/usr/bin/env python3
"""solution-design 문서의 기계적 점검.

판단이 필요 없는 결함만 짚는다. 결정이 타당한지·지어냈는지는 검토 에이전트(review-rubric.md)가 맡는다.

    python3 check_solution.py <설계 문서> [--problem <문제 정의 문서>]

--problem을 주면 결정이 가리키는 KR이 문제 정의에 실제로 있는지도 본다.
종료 코드: 오류가 있으면 1, 경고만 있거나 깨끗하면 0.
"""

import argparse
import re
import sys
from pathlib import Path

DECISION_ROW = re.compile(r"^\|\s*(D\d+)\s*\|")
KR_REF = re.compile(r"O\d+(?:\.\d+)*\s+KR\d+")
PROBLEM_KR_ROW = re.compile(r"^\|\s*(O[\d.]+)\s*\|\s*(KR\d+)\s*\|")
PROBLEM_LINE = re.compile(r"^\s*-\s*문제 정의\s*:\s*(.*)$", re.M)
H2 = re.compile(r"^##(?!#)\s*(.*)$")
# 문제 정의·플랜이 맡는 절. "기술 리스크 / 선행 검증"은 설계 몫이라 뺀다.
FOREIGN = re.compile(r"배경|목표|성공 지표|검증 방법|작업|일정|코드 리뷰|브랜치|문제 정의|리스크|미루는|하지 않는")
TASK = re.compile(r"^\s*- \[[ xX]\] ")
EMPTY = ("", "-", "—")


def problem_krs(text: str) -> set[str]:
    return {f"{m.group(1)} {m.group(2)}" for line in text.splitlines() if (m := PROBLEM_KR_ROW.match(line))}


def check(text: str, problem: str | None = None):
    errors, warnings = [], []
    header = PROBLEM_LINE.search(text)
    skipped = bool(header and "생략" in header.group(1))
    if not header or not header.group(1).strip():
        errors.append("머리말에 `- 문제 정의:` 줄이 없거나 비어 있음 — 위치를 적거나 `생략 (<이유>)`")
    known = problem_krs(problem) if problem is not None else None

    seen = set()
    for n, line in enumerate(text.splitlines(), 1):
        h = H2.match(line)
        if h and FOREIGN.search(h.group(1)) and "기술 리스크" not in h.group(1):
            errors.append(f"{n}: 설계에 오지 않는 절 — {line.strip()[:60]} (문제·목표는 문제 정의, 작업·일정·검증·리스크는 플랜)")
        if TASK.match(line):
            errors.append(f"{n}: 작업 체크박스 — 작업은 work-plan 문서에 둔다: {line.strip()[:60]}")

        d = DECISION_ROW.match(line)
        if not d:
            continue
        did = d.group(1)
        if did in seen:
            errors.append(f"{n}: {did}가 두 번 나옴 — 플랜이 이 번호로 가리키므로 겹치면 안 됨")
        seen.add(did)
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4:
            errors.append(f"{n}: {did} 행의 칸 수가 4가 아님({len(cells)}) — | # | 결정 | 이유 | KR |")
            continue
        _, decision, reason, kr = cells
        if decision in EMPTY:
            errors.append(f"{n}: {did}의 결정이 비어 있음")
        if reason in EMPTY:
            errors.append(f"{n}: {did}의 이유가 비어 있음")
        refs = KR_REF.findall(kr)
        if not refs:
            if kr in EMPTY and skipped:
                continue
            errors.append(f"{n}: {did}의 KR 칸이 `O1.1 KR1` 형식이 아님: {kr!r} (문제 정의를 생략했을 때만 `—`)")
            continue
        if known is not None:
            for ref in refs:
                if " ".join(ref.split()) not in known:
                    errors.append(f"{n}: {did}가 문제 정의에 없는 {ref}를 가리킴")

    if not seen:
        errors.append("결정 표 행을 찾지 못함 (| D1 | 결정 | 이유 | KR | 형식)")
    if known is not None:
        used = {" ".join(r.split()) for line in text.splitlines() if DECISION_ROW.match(line) for r in KR_REF.findall(line)}
        for kr in sorted(known - used):
            warnings.append(f"{kr}에 기여하는 결정이 없음 — 설계로 풀 필요가 없으면 미해결 설계 사안이나 이유를 적을 것")
    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design")
    ap.add_argument("--problem")
    args = ap.parse_args()
    problem = Path(args.problem).read_text(encoding="utf-8") if args.problem else None
    errors, warnings = check(Path(args.design).read_text(encoding="utf-8"), problem)
    for e in errors:
        print(f"오류 {e}")
    for w in warnings:
        print(f"경고 {w}")
    print(f"결과: 오류 {len(errors)} / 경고 {len(warnings)}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
