#!/usr/bin/env python3
"""problem-definition 문서의 기계적 점검.

판단이 필요 없는 결함만 짚는다. 지어냈는지·해법이 섞였는지 같은 판단은 검토 에이전트(review-rubric.md)가 맡는다.

    python3 check_problem.py <문서 경로>

종료 코드: 오류가 있으면 1, 경고만 있거나 깨끗하면 0.
"""

import re
import sys
from pathlib import Path

KR_ROW = re.compile(r"^\|\s*(O[\d.]+)\s*\|\s*(KR\d+)\s*\|")
OBJ_ID = re.compile(r"\bO\d+(?:\.\d+)*\b")
METHODS = ("확인", "에이전트 채점", "사람 판정")
KINDS = ("약속", "도전")
NUMERIC = re.compile(r"\d+(\.\d+)?\s*(%|퍼센트|명|건|개|회|배|초|분|시간|일|주|원|안|장|곳|단계)")
# 다른 문서(설계·플랜)가 맡는 절. 제목에 이 말이 들어가면 이 문서에 있을 내용이 아니다.
FOREIGN_HEADING = re.compile(r"^##(?!#)\s*(\d+[.)]?\s*)?.*(작업|일정|기한 판정|위험|리스크|요구사항|하지 않는)")
TASK = re.compile(r"^\s*- \[[ xX]\] ")


def check(text: str):
    errors, warnings = [], []
    lines = text.splitlines()
    defined = set()
    for line in lines:
        if not KR_ROW.match(line):
            defined.update(OBJ_ID.findall(line))

    seen = set()
    for n, line in enumerate(lines, 1):
        if FOREIGN_HEADING.match(line):
            errors.append(f"{n}: 문제 정의에 오지 않는 절 — {line.strip()[:60]} (설계는 solution-design, 작업·일정·위험은 work-plan)")
        if TASK.match(line):
            errors.append(f"{n}: 작업 체크박스 — 작업은 work-plan 문서에 둔다: {line.strip()[:60]}")

        k = KR_ROW.match(line)
        if not k:
            continue
        obj, kr = k.group(1), k.group(2)
        if (obj, kr) in seen:
            errors.append(f"{n}: {obj} {kr}가 두 번 나옴 — 설계·플랜이 이 이름으로 가리키므로 겹치면 안 됨")
        seen.add((obj, kr))
        if obj not in defined:
            errors.append(f"{n}: {obj}가 목표 트리·문제 정의에 없음")
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            errors.append(f"{n}: KR 행의 칸 수가 6이 아님({len(cells)}) — {obj} {kr}")
            continue
        _, _, criterion, method, when, kind = cells
        for name, value in (("판정 기준", criterion), ("판정 시점", when)):
            if not value or value in ("-", "—"):
                errors.append(f"{n}: {obj} {kr}의 {name}가 비어 있음")
        if not any(x in method for x in METHODS):
            errors.append(f"{n}: {obj} {kr}의 판정 방법이 허용값({'/'.join(METHODS)})이 아님: {method}")
        if not any(x in kind for x in KINDS):
            errors.append(f"{n}: {obj} {kr}의 유형이 허용값({'/'.join(KINDS)})이 아님: {kind}")
        if NUMERIC.search(criterion) and "후보" not in criterion:
            warnings.append(f"{n}: {obj} {kr}에 수치가 있는데 `후보:` 표시가 없음 — 사용자가 준 값이 아니면 표시할 것")

    if not seen:
        errors.append("KR 표 행을 찾지 못함 (| O1 | KR1 | ... 형식)")
    return errors, warnings


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    errors, warnings = check(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for e in errors:
        print(f"오류 {e}")
    for w in warnings:
        print(f"경고 {w}")
    print(f"결과: 오류 {len(errors)} / 경고 {len(warnings)}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
