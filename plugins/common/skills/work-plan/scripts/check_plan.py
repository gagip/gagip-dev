#!/usr/bin/env python3
"""work-plan 문서의 기계적 점검.

판단이 필요 없는 결함만 짚는다. 담당이 맞는지·앞 단계가 타당한지·지어냈는지는 검토 에이전트(review-rubric.md)가 맡는다.

    python3 check_plan.py <플랜 문서> [--design <설계 문서>] [--problem <문제 정의 문서>]

--design을 주면 작업이 가리키는 결정이 설계에 있는지, 모든 결정이 작업이나 미루는 작업에 있는지 본다.
--problem을 주면 작업이 가리키는 KR이 문제 정의에 있는지, 모든 KR에 검증 방법이 있는지 본다.
종료 코드: 오류가 있으면 1, 경고만 있거나 깨끗하면 0.
"""

import argparse
import re
import sys
from pathlib import Path

LABEL = re.compile(r"^(사람\((설계|결정|리뷰|실물)\)|에이전트)\s*:")
TASK = re.compile(r"^\s*- \[[ xX]\] (.+)$")
TRACE = re.compile(r"\[([^\[\]]+)\]\s*$")
DATE = re.compile(r"\d{1,2}/\d{1,2}|[월화수목금토일]요일")
DECISION = re.compile(r"\bD\d+\b")
KR_REF = re.compile(r"O\d+(?:\.\d+)*\s+KR\d+")
DECISION_ROW = re.compile(r"^\|\s*(D\d+)\s*\|")
PROBLEM_KR_ROW = re.compile(r"^\|\s*(O[\d.]+)\s*\|\s*(KR\d+)\s*\|")
H2 = re.compile(r"^##(?!#)\s*(.*)$")
# 문제 정의·설계가 맡는 절. 여기 오면 두 번 쓰는 것이다.
FOREIGN = re.compile(r"배경|문제 정의|목표 트리|OKR|판정 기준|요구사항|제약|기술 리스크|선행 검증|미해결 설계")
REVIEW_DONE = re.compile(r"승인|반려|확정|받아들|돌려보|판정|통과|기록|반영")
# "코드를 한 곳에 모은다" 같은 정리 작업은 수집이 아니라서 대상을 좁힌다
COLLECT = re.compile(r"수집|(사례|자료|예시|의견|피드백|레퍼런스)\S*\s*모[은으]")
NUMERIC = re.compile(r"\d+\s*(건|개|곳|명|회|장)")
STATUS = re.compile(r"^\s*-\s*상태\s*:\s*(초안|승인됨 \(\d{4}-\d{2}-\d{2}\))\s*$", re.M)
SUBMIT = re.compile(r"^(초안( \(커밋까지\))?|push·PR까지)$")
OPEN_HUMAN_TASK = re.compile(r"^\s*- \[ \] 사람\(")


def header(text: str, name: str) -> str | None:
    m = re.search(rf"^\s*-\s*{name}\s*:\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else None


def sections(text: str) -> dict[str, str]:
    """## 절 제목 → 본문. 번호는 떼고 담는다."""
    out, title, buf = {}, None, []
    for line in text.splitlines():
        h = H2.match(line)
        if h:
            if title is not None:
                out[title] = "\n".join(buf)
            title, buf = re.sub(r"^\d+[.)]?\s*", "", h.group(1)).strip(), []
        elif title is not None:
            buf.append(line)
    if title is not None:
        out[title] = "\n".join(buf)
    return out


def section(secs: dict[str, str], keyword: str) -> str | None:
    return next((body for title, body in secs.items() if keyword in title), None)


def norm(ref: str) -> str:
    return " ".join(ref.split())


def field(body: str, name: str) -> tuple[str, list[str]] | None:
    """`- 이름: 값` 줄의 값과, 그 아래 들여 쓴 `- ` 항목들."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        m = re.match(rf"^-\s*{name}\s*:\s*(.*)$", line)
        if not m:
            continue
        children = []
        for child in lines[i + 1:]:
            if not child.strip():
                continue
            c = re.match(r"^\s+-\s+(.+)$", child)
            if not c:
                break
            children.append(c.group(1).strip())
        return m.group(1).strip(), children
    return None


def written(value: str) -> bool:
    return bool(value) and not value.startswith("<")


def filled(f: tuple[str, list[str]] | None) -> bool:
    if f is None:
        return False
    value, children = f
    return written(value) or any(written(c) for c in children)


def table_rows(body: str) -> list[str]:
    """표의 데이터 행. 머리 행·구분 행과, 빈 칸이나 `<...>` 자리표시 칸이 있는 행은 뺀다."""
    rows, in_table = [], False
    for line in body.splitlines():
        if not line.startswith("|"):
            in_table = False
            continue
        if not in_table:
            in_table = True
            continue
        if re.match(r"^\|[\s\-:|]+\|\s*$", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(written(c) for c in cells):
            rows.append(line)
    return rows


def check_agreement(text: str, secs: dict[str, str], errors: list[str], warnings: list[str]):
    body = section(secs, "착수 전 합의")
    if body is None:
        errors.append("착수 전 합의 절이 없음 — 제출·준비물·착수 뒤 사람 몫·멈춤 전제를 승인 전에 정한다")
        return
    submit = field(body, "제출")
    if submit is None or not SUBMIT.match(submit[0]):
        errors.append("착수 전 합의에 `- 제출:`이 `초안` 또는 `push·PR까지`로 적혀 있지 않음")
    if not filled(field(body, "준비물")):
        errors.append("착수 전 합의에 `- 준비물:`이 비어 있음 — 없으면 `없음`")
    if not table_rows(body):
        errors.append("멈춤 전제가 없음 — 착수 전 합의 절의 표에 이 플랜이 기대는 사실과 깨졌다고 보는 관찰을 적는다")

    after = field(body, "착수 뒤 사람 몫")
    if not filled(after):
        errors.append("착수 전 합의에 `- 착수 뒤 사람 몫:`이 비어 있음 — 없으면 `없음`")
        return
    open_human = [l.strip()[6:] for l in text.splitlines() if OPEN_HUMAN_TASK.match(l)]
    if not any(written(c) for c in after[1]) and open_human:
        msg = (f"착수 뒤 사람 몫에 적힌 작업이 없는데 끝나지 않은 사람 작업이 {len(open_human)}개 있음 — 승인 전에 "
               f"끝내 `[x]`로 바꾸거나, 착수 뒤 사람 몫 아래 항목으로 적는다(최종 보고 때 받는 리뷰 포함): "
               f"{open_human[0][:60]}")
        status = STATUS.search(text)
        (errors if status and status.group(1).startswith("승인됨") else warnings).append(msg)


def check(text: str, design: str | None = None, problem: str | None = None):
    errors, warnings = [], []
    lines = text.splitlines()
    secs = sections(text)

    for name in ("문제 정의", "설계"):
        value = header(text, name)
        if not value:
            errors.append(f"머리말에 `- {name}:` 줄이 없거나 비어 있음 — 위치를 적거나 `생략 (<이유>)`")
    if not STATUS.search(text):
        errors.append("머리말 `- 상태:`가 `초안` 또는 `승인됨 (YYYY-MM-DD)`가 아님")

    deadline = header(text, "기한")
    schedule = section(secs, "일정")
    if deadline is None:
        errors.append("머리말에 `- 기한:` 줄이 없음 — 없으면 `없음`")
    elif deadline.startswith("없음"):
        if schedule is not None:
            warnings.append("기한이 없음인데 일정 절이 있음 — 기한이 없으면 일정 절을 지운다")
    elif schedule is None or "기한" not in schedule:
        errors.append(f"기한({deadline})이 있는데 일정과 기한 판정 절이 없음")

    known_d = {m.group(1) for l in design.splitlines() if (m := DECISION_ROW.match(l))} if design is not None else None
    known_kr = (
        {f"{m.group(1)} {m.group(2)}" for l in problem.splitlines() if (m := PROBLEM_KR_ROW.match(l))}
        if problem is not None
        else None
    )

    traced_d, task_count = set(), 0
    for n, line in enumerate(lines, 1):
        h = H2.match(line)
        if h and FOREIGN.search(h.group(1)):
            errors.append(f"{n}: 플랜에 오지 않는 절 — {line.strip()[:60]} (문제·판정 기준은 문제 정의, 결정·제약·기술 리스크는 설계)")
        m = TASK.match(line)
        if not m:
            continue
        body = m.group(1)
        task_count += 1
        before_dep = body.split("←")[0]
        if not LABEL.match(body):
            errors.append(f"{n}: 담당 표시 없음 — {body[:60]}")
        elif body.startswith("에이전트") and DATE.search(before_dep):
            errors.append(f"{n}: 에이전트 항목에 날짜가 붙음 — {body[:60]}")
        if body.startswith("사람(리뷰)") and not REVIEW_DONE.search(body):
            warnings.append(f"{n}: 리뷰 항목에 끝나는 조건(승인·반려·확정 등)이 없음 — {body[:60]}")
        if COLLECT.search(before_dep) and not NUMERIC.search(body):
            warnings.append(f"{n}: 수집 항목에 끝나는 조건(몇 건까지)이 없음 — {body[:60]}")

        t = TRACE.search(body)
        refs_d = DECISION.findall(t.group(1)) if t else []
        refs_kr = [norm(r) for r in KR_REF.findall(t.group(1))] if t else []
        if not t or not (refs_d or refs_kr or "공통" in t.group(1)):
            errors.append(f"{n}: 대응 대상이 없음 — 끝에 `[D1]`·`[O1.1 KR1]`·`[공통]`을 붙일 것: {body[:60]}")
            continue
        traced_d.update(refs_d)
        if known_d is not None:
            for d in refs_d:
                if d not in known_d:
                    errors.append(f"{n}: 설계에 없는 {d}를 가리킴")
        if known_kr is not None:
            for kr in refs_kr:
                if kr not in known_kr:
                    errors.append(f"{n}: 문제 정의에 없는 {kr}를 가리킴")

    if task_count == 0:
        errors.append("작업 항목을 찾지 못함 (- [ ] <담당>: <작업> [<대응 대상>] 형식)")

    if known_d is not None:
        # 작업 범위 절에서 "이번에 하는 것" 줄을 뺀 나머지(미루는 작업)에 적힌 결정은 작업이 없어도 된다
        scope = section(secs, "작업 범위") or ""
        deferred = set(DECISION.findall("\n".join(l for l in scope.splitlines() if "이번에 하는" not in l)))
        for d in sorted(known_d - traced_d - deferred, key=lambda x: int(x[1:])):
            errors.append(f"{d}를 이루는 작업이 없음 — 작업을 붙이거나 미루는 작업에 이유와 함께 적을 것")

    verify = section(secs, "검증")
    if verify is None:
        errors.append("검증 방법 절이 없음")
    elif known_kr is not None:
        verified = {norm(r) for l in verify.splitlines() if l.startswith("|") for r in KR_REF.findall(l.split("|")[1])}
        for kr in sorted(known_kr - verified):
            errors.append(f"{kr}의 검증 방법이 없음 — 검증 방법 표에 행을 추가할 것")

    check_agreement(text, secs, errors, warnings)
    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--design")
    ap.add_argument("--problem")
    args = ap.parse_args()
    read = lambda p: Path(p).read_text(encoding="utf-8") if p else None  # noqa: E731
    errors, warnings = check(read(args.plan), read(args.design), read(args.problem))
    for e in errors:
        print(f"오류 {e}")
    for w in warnings:
        print(f"경고 {w}")
    print(f"결과: 오류 {len(errors)} / 경고 {len(warnings)}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
