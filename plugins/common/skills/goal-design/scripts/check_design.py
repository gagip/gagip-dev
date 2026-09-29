#!/usr/bin/env python3
"""goal-design 문서의 기계적 점검.

판단이 필요 없는 결함만 짚는다. 지어냈는지·충분한지 같은 판단은 검토 에이전트(review-rubric.md)가 맡는다.

    python3 check_design.py <문서 경로>

종료 코드: 오류가 있으면 1, 경고만 있거나 깨끗하면 0.
"""

import re
import sys
from pathlib import Path

LABEL = re.compile(r"^(사람\((설계|결정|리뷰|실물)\)|에이전트)\s*:")
TASK = re.compile(r"^\s*- \[[ xX]\] (.+)$")
DATE = re.compile(r"\d{1,2}/\d{1,2}|[월화수목금토일]요일")
KR_ROW = re.compile(r"^\|\s*(O[\d.]+)\s*\|\s*(KR\d+)\s*\|")
METHODS = ("확인", "에이전트 채점", "사람 판정")
KINDS = ("약속", "도전")
NUMERIC = re.compile(r"\d+(\.\d+)?\s*(%|퍼센트|명|건|개|회|배|초|분|시간|일|주|원|안|장|곳|단계)")
SECTION = re.compile(r"^###\s+(O\d+(?:\.\d+)*)\b")
REVIEW_DONE = re.compile(r"승인|반려|확정|받아들|돌려보|판정|통과|기록|반영")
COLLECT = re.compile(r"모은다|모으기|수집한다")
REF = re.compile(r"←\s*(.+)$")
ID = re.compile(r"\b(O\d+(?:\.\d+)*|KR\d+)\b")


def check(text: str):
    errors, warnings = [], []
    lines = text.splitlines()
    defined = set(ID.findall(text.split("## 4.", 1)[0])) if "## 4." in text else set(ID.findall(text))

    section = None
    for n, line in enumerate(lines, 1):
        s = SECTION.match(line)
        if s:
            section = s.group(1)
        m = TASK.match(line)
        if m:
            body = m.group(1)
            if not LABEL.match(body):
                errors.append(f"{n}: 담당 표시 없음 — {body[:60]}")
            elif body.startswith("에이전트") and DATE.search(body.split("←")[0]):
                errors.append(f"{n}: 에이전트 항목에 날짜가 붙음 — {body[:60]}")
            if body.startswith("사람(리뷰)") and not REVIEW_DONE.search(body):
                warnings.append(f"{n}: 리뷰 항목에 끝나는 조건(승인·반려·확정 등)이 없음 — {body[:60]}")
            if COLLECT.search(body.split("←")[0]) and not NUMERIC.search(body):
                warnings.append(f"{n}: 수집 항목에 끝나는 조건(몇 건까지)이 없음 — {body[:60]}")
            ref = REF.search(body)
            if ref:
                for rid in ID.findall(ref.group(1)):
                    if rid not in defined:
                        errors.append(f"{n}: 앞 단계가 정의되지 않은 {rid}를 가리킴")
                # 번호만 달랑 적은 앞 단계("← O1.1")가 자기 소속 절이면 자기 자신을 기다리는 모양이다.
                # "← O1.1 목록 작성"처럼 작업 이름이 붙으면 같은 절 안의 특정 작업이라 정상이다.
                if section:
                    for item in re.split(r"[,，、]", ref.group(1)):
                        if item.strip().split(" ")[0].strip("*`()") == section and len(item.strip().split()) == 1:
                            errors.append(f"{n}: 작업이 자기가 속한 {section}를 앞 단계로 가리킴 — 그 안의 구체 작업을 가리킬 것")

        k = KR_ROW.match(line)
        if k:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 6:
                errors.append(f"{n}: KR 행의 칸 수가 6이 아님({len(cells)}) — {k.group(1)} {k.group(2)}")
                continue
            _, _, criterion, method, when, kind = cells
            for name, value in (("판정 기준", criterion), ("판정 시점", when)):
                if not value or value in ("-", "—"):
                    errors.append(f"{n}: {k.group(1)} {k.group(2)}의 {name}가 비어 있음")
            if not any(x in method for x in METHODS):
                errors.append(f"{n}: {k.group(1)} {k.group(2)}의 판정 방법이 허용값({'/'.join(METHODS)})이 아님: {method}")
            if not any(x in kind for x in KINDS):
                errors.append(f"{n}: {k.group(1)} {k.group(2)}의 유형이 허용값({'/'.join(KINDS)})이 아님: {kind}")
            if NUMERIC.search(criterion) and "후보" not in criterion:
                warnings.append(
                    f"{n}: {k.group(1)} {k.group(2)}에 수치가 있는데 `후보:` 표시가 없음 — 사용자가 준 값이 아니면 표시할 것"
                )

    if not any(KR_ROW.match(l) for l in lines):
        errors.append("KR 표 행을 찾지 못함 (| O1 | KR1 | ... 형식)")
    return errors, warnings


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    path = Path(sys.argv[1])
    errors, warnings = check(path.read_text(encoding="utf-8"))
    for e in errors:
        print(f"오류 {e}")
    for w in warnings:
        print(f"경고 {w}")
    print(f"결과: 오류 {len(errors)} / 경고 {len(warnings)}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
