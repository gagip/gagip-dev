"""단계 관문 — 다음 단계로 넘어가도 되는지 결정론적으로 검사한다.

왜 스크립트인가: 마크다운에 적은 지시는 확률적으로 무시된다.
넘어가도 되는지의 판정은 모델이 아니라 코드가 한다.

디자인 부서 관문과 다른 점: 여기서는 산출물 텍스트만 보지 않고 **실제 git 명령을
돌린다**. 구현했는지·커밋 작성자가 맞는지는 마크다운에 뭐라고 적혀 있든 저장소가
정답이기 때문이다. git 호출은 싸다 — 빌드·테스트를 관문이 돌리지 않는 것과는 다른
판단이다(그건 느려서 결국 안 돌리게 된다).

무엇을 검사하지 않는가: 구현이 좋은지는 검사하지 않는다. 여기서 보는 것은
"그 단계가 내놓기로 한 상태가 실제로 만들어졌는가"뿐이다.

실행:
    python3 gate.py <사이클 폴더>              기록된 단계의 읽기 전용 진단
    python3 gate.py <사이클 폴더> --stage review  한 단계만

상태 조회·진행 승인은 cycle.py가 담당한다. 이 진단은 상태를 저장하지 않는다.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import handoff  # noqa: E402
import mdsec  # noqa: E402
from handoff import (  # noqa: E402
    STATE_DONE, STATE_SKIPPED, STATUS_OPEN, Handoff, StageRow,
)

# 브랜치 명명 — 기존 관행(최근 머지 PR 전량이 이 형식).
BRANCH_RE = re.compile(r"^(feat|fix|docs|chore|refactor|test)/\d+-[a-z0-9][a-z0-9-]*$")

# 커밋 제목. Jira 이슈 키가 있을 때만 대괄호 접두어를 허용한다.
COMMIT_SUBJECT_RE = re.compile(
    r"^(\[[A-Z][A-Z0-9]*-\d+\] )?(feat|fix|test|refactor|chore|docs)(\(.+\))?: .+"
)

# 출처 표기 — 이슈 번호 또는 조직 인계 폴더의 명세 파일.
ISSUE_RE = re.compile(r"#(\d+)\b")
PR_URL_RE = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/pull/\d+")

# 리뷰 판정에서 고쳐야만 넘어갈 수 있는 등급. 스타일(🟡)은 커밋을 막지 않는다.
BLOCKING_MARK = "🔴"
# 부정형을 먼저 본다 — "미반영"은 "반영"을 부분 문자열로 품고 있어서, 긍정어만
# 찾으면 미반영이 반영으로 통과한다(test_gate.py가 실제로 잡아낸 결함).
NOT_APPLIED_RE = re.compile(r"미반영|미수정|안\s*함|보류|없음")
APPLIED_RE = re.compile(r"반영|수정|고침|완료")


class GateError(Exception):
    """관문이 판정에 필요한 것을 못 얻었다. 추측해서 통과시키지 않는다."""


def _git(repo: Path, *args: str) -> str:
    """작업 레포에서 git을 돌려 표준출력을 돌려준다. 실패는 GateError."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GateError(f"git 실행 실패({' '.join(args)}): {exc}") from None
    if proc.returncode != 0:
        raise GateError(f"git {' '.join(args)} 실패: {proc.stderr.strip()}")
    return proc.stdout


def _repo(h: Handoff) -> Path:
    """작업 레포. 머리말이 정본이다 — 산출물 마크다운을 파싱해 얻지 않는다."""
    raw = h.meta.get("repo", "").strip()
    if not raw:
        raise GateError("머리말의 `repo`가 비어 있다 — branch 단계가 채워야 한다")
    path = Path(raw).expanduser()
    if not (path / ".git").exists():
        raise GateError(f"git 저장소가 아니다: {path}")
    return path


def _base(h: Handoff) -> str:
    """브랜치를 딴 기준. 빈 값을 main으로 조용히 대체하지 않는다 —
    기본 브랜치가 develop인 레포에서 엉뚱한 커밋 집합을 검사하게 된다."""
    base = h.meta.get("base", "").strip()
    if not base:
        raise GateError("머리말의 `base`가 비어 있다 — 브랜치를 딴 기준을 적어야 한다")
    return base


def _artifact(cycle_dir: Path, row: StageRow) -> tuple[Path | None, list[str]]:
    """산출물 경로를 돌려준다. 표에 안 적혔거나 파일이 없으면 실패 사유를 함께."""
    if not row.artifact:
        return None, [f"'{row.key}' 단계의 산출물 칸이 비어 있다"]
    path = cycle_dir / row.artifact
    if not path.exists():
        return None, [f"산출물이 없다: {row.artifact}"]
    return path, []


def _require_sections(text: str, titles: tuple[str, ...]) -> list[str]:
    return [f"`## {t}` 절이 없다" for t in titles if mdsec.section(text, t) is None]


def _require_evidence(h: Handoff, row: StageRow, title: str, empty_hint: str) -> list[str]:
    """`## title` 절에 목록이 있거나 '없음'이라고 적혀 있어야 한다.

    "볼 게 없었다"와 "안 봤다"를 가르는 것이 이 검사의 전부다. 두 단계(simplify·docs)가
    같은 성격인데 각자 다른 강도로 구현돼 있었다 — 한쪽은 아무 글자나 있으면 통과했다.
    """
    path, fails = _artifact(h.cycle_dir, row)
    if fails:
        return fails
    body = mdsec.section(path.read_text(encoding="utf-8"), title)
    if body is None:
        return [f"`## {title}` 절이 없다"]
    if "없음" not in body and not mdsec.bullets(body):
        fails.append(f"{empty_hint} — 점검 자체를 건너뛴 것으로 본다")
    return fails


def _check_intake(h: Handoff, row: StageRow) -> list[str]:
    """작업 명세 정규화. 이슈든 인계 파일이든 여기서 같은 형식이 된다.

    이 단계가 무르면 뒤가 전부 무르다 — 무엇을 고치는지·무엇으로 끝났다고 할지가
    안 정해진 채로 구현이 시작된다.
    """
    path, fails = _artifact(h.cycle_dir, row)
    if fails:
        return fails
    text = path.read_text(encoding="utf-8")
    fails += _require_sections(text, ("출처", "무엇을 고치나", "검증 조건", "범위 밖"))
    if fails:
        return fails

    origin = mdsec.section(text, "출처") or ""
    if not ISSUE_RE.search(origin):
        fails.append("출처에 이슈 번호(#N)가 없다")

    conditions = mdsec.bullets(mdsec.section(text, "검증 조건") or "")
    if not conditions:
        fails.append("검증 조건이 하나도 없다 — 무엇으로 끝났다고 할지가 안 정해졌다")
    else:
        vague = [c for c in conditions if "`" not in c and "사람 확인" not in c]
        if vague:
            fails.append(
                f"검증 조건 {len(vague)}건이 실행 가능한 명령(백틱)도 '사람 확인' 표시도 "
                f"아니다 — 첫 건: {vague[0][:40]}"
            )
    return fails


def _check_branch(h: Handoff, row: StageRow) -> list[str]:
    """브랜치·작업 위치. 메인 워크트리는 사용자 자리라 기본적으로 막는다."""
    _, fails = _artifact(h.cycle_dir, row)
    if fails:
        return fails

    branch = h.meta.get("branch", "").strip()
    if not branch:
        return ["머리말의 `branch`가 비어 있다"]
    if not BRANCH_RE.match(branch):
        fails.append(f"브랜치명이 `<타입>/<이슈번호>-<슬러그>` 형식이 아니다 — {branch!r}")

    repo = _repo(h)
    actual = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if actual != branch:
        fails.append(f"레포의 현재 브랜치가 머리말과 다르다 — 파일 {branch!r} / 실제 {actual!r}")

    git_dir = _git(repo, "rev-parse", "--absolute-git-dir").strip()
    common_dir = _git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    if git_dir == common_dir and h.meta.get("allow_main", "").strip().lower() != "true":
        fails.append(
            "메인 워크트리에서 작업 중이다 — 별도 워크트리를 쓰거나, 의도된 예외면 "
            "머리말에 `allow_main: true`를 적는다"
        )
    return fails


def _check_implement(h: Handoff, row: StageRow) -> list[str]:
    """구현. 실제로 무언가 바뀌었는지는 저장소에 묻는다."""
    _, fails = _artifact(h.cycle_dir, row)
    if fails:
        return fails

    repo = _repo(h)
    base = _base(h)
    committed = _git(repo, "log", f"{base}..HEAD", "--oneline").strip()
    dirty = _git(repo, "status", "--porcelain").strip()
    if not committed and not dirty:
        fails.append(f"{base} 대비 바뀐 것이 없다 — 커밋도 작업트리 변경도 없다")
    return fails


def _check_simplify(h: Handoff, row: StageRow) -> list[str]:
    """정리. 무엇을 정리했는지(없으면 없다고) 남아야 다음 사람이 중복해서 안 훑는다."""
    return _require_evidence(h, row, "정리 결과", "정리한 것의 목록도 '없음'도 없다")


def _check_review(h: Handoff, row: StageRow) -> list[str]:
    """코드 리뷰. 🔴은 전부 반영돼야 넘어간다. 🟡은 막지 않는다.

    표의 마지막 칸을 반영 여부로 읽는다 — 열 이름을 강제하는 대신 위치로 읽으면
    산출물 형식이 조금 달라져도 판정이 흔들리지 않는다.
    """
    path, fails = _artifact(h.cycle_dir, row)
    if fails:
        return fails
    body = mdsec.section(path.read_text(encoding="utf-8"), "판정")
    if body is None:
        return ["`## 판정` 절이 없다"]

    rows = mdsec.table_rows(body)
    if not rows:
        if BLOCKING_MARK not in body and "없음" not in body:
            fails.append("판정 표도 '없음' 표시도 없다 — 리뷰를 했는지 알 수 없다")
        return fails

    for cells in rows:
        if BLOCKING_MARK not in cells[0]:
            continue
        applied = cells[-1]
        if NOT_APPLIED_RE.search(applied) or not APPLIED_RE.search(applied):
            fails.append(
                f"{BLOCKING_MARK} 지적이 반영되지 않았다 — {cells[1][:40] if len(cells) > 1 else ''} "
                f"(반영 칸: {applied!r})"
            )
    return fails


def _check_docs(h: Handoff, row: StageRow) -> list[str]:
    """문서 영향 점검. 볼 게 없었다는 것과 안 봤다는 것을 구분한다."""
    return _require_evidence(h, row, "문서 영향", "고친 문서 목록도 '문서 영향 없음'도 없다")


def _commit_failures(h: Handoff) -> list[str]:
    """제출·종결 전에 실제 커밋과 남은 변경을 검사한다."""
    fails = []
    repo = _repo(h)
    base = _base(h)

    dirty = _git(repo, "status", "--porcelain").strip()
    if dirty:
        fails.append(f"작업트리가 깨끗하지 않다 — 커밋되지 않은 변경 {len(dirty.splitlines())}건")

    log = _git(repo, "log", f"{base}..HEAD", "--format=%ae%x00%s").strip()
    if not log:
        return fails + [f"{base} 대비 커밋이 없다"]

    expected = _git(repo, "config", "user.email").strip()
    for line in log.splitlines():
        email, _, subject = line.partition("\x00")
        if email != expected:
            fails.append(
                f"커밋 작성자가 레포 git 설정과 다르다 — {email!r} (설정: {expected!r}) "
                f"· 커밋: {subject[:40]}"
            )
        if not COMMIT_SUBJECT_RE.match(subject):
            fails.append(f"커밋 메시지가 `타입: 한글 메시지` 형식이 아니다 — {subject[:50]!r}")
    return fails


def check_commits(h: Handoff) -> tuple[bool, list[str]]:
    try:
        fails = _commit_failures(h)
    except GateError as exc:
        fails = [str(exc)]
    return (not fails), fails


def _check_ship(h: Handoff, row: StageRow) -> list[str]:
    """push·PR. 초안 모드에서는 이 단계를 '생략'으로 두므로 여기 오지 않는다."""
    path, fails = _artifact(h.cycle_dir, row)
    if fails:
        return fails
    if not PR_URL_RE.search(path.read_text(encoding="utf-8")):
        fails.append("PR URL이 없다 — 올렸으면 주소를, 안 올렸으면 단계를 '생략'으로 둔다")
    fails.extend(_commit_failures(h))
    return fails


def _check_close(h: Handoff, row: StageRow) -> list[str]:
    """사이클 종료. 리뷰에 🔴이 남아 있으면 닫지 못한다."""
    path, fails = _artifact(h.cycle_dir, row)
    if fails:
        return fails
    text = path.read_text(encoding="utf-8")

    body = mdsec.section(text, "종결")
    if body is None:
        return ["`## 종결` 절이 없다"]
    status = h.meta["status"]
    if status == STATUS_OPEN:
        fails.append(f"머리말 status가 '{STATUS_OPEN}'이다 — 2값 중 하나로 닫아야 한다")
    elif status not in body:
        fails.append(f"종결 절에 종결값 '{status}'가 적혀 있지 않다")

    review_row = h.stage("review")
    if review_row.state == STATE_DONE and review_row.artifact:
        left = _check_review(h, review_row)
        if left:
            fails.append(f"리뷰 지적이 아직 남아 있다 ({len(left)}건) — 반영 전엔 종료할 수 없다")
    fails.extend(_commit_failures(h))
    return fails


# 단계별 관문. 모든 단계에서 실제로 검사한다 — '존재만' 확인하는 약한
# 단계가 없어서 엄격도 칸을 따로 두지 않는다(생략된 단계는 상태 칸이 이미 말한다).
CHECKS = {
    "intake": _check_intake,
    "branch": _check_branch,
    "implement": _check_implement,
    "simplify": _check_simplify,
    "review": _check_review,
    "docs": _check_docs,
    "ship": _check_ship,
    "close": _check_close,
}
assert set(CHECKS) == set(handoff.STAGE_KEYS), "관문 정의가 파이프라인 정의와 어긋난다"


def check_stage(h: Handoff, key: str) -> tuple[bool, list[str]]:
    row = h.stage(key)
    if row.state == STATE_SKIPPED:
        return True, []
    try:
        fails = CHECKS[key](h, row)
    except GateError as exc:
        fails = [str(exc)]
    return (not fails), fails


def run(cycle_dir: Path, only: str | None) -> int:
    h = handoff.load(cycle_dir)
    keys = [only] if only else [
        s.key for s in h.stages if s.state in (STATE_DONE, STATE_SKIPPED)
    ]

    print(f"사이클: {h.meta['cycle_id']} — {h.meta['title']}")
    print(f"종결값: {h.meta['status']}")

    if not keys:
        print("\n완료로 표시된 단계가 없다 — 검사할 것이 없음")
    else:
        print()
        failed = 0
        for key in keys:
            ok, fails = check_stage(h, key)
            row = h.stage(key)
            mark = "✅" if ok else "❌"
            note = " (생략)" if row.state == STATE_SKIPPED else ""
            print(f"{mark} {key:10s} {row.name:16s}{note}")
            for f in fails:
                print(f"      ↳ {f}")
            if not ok:
                failed += 1
        if failed:
            print(f"\n{failed}개 단계가 관문을 넘지 못했다 — 고친 뒤 다시 돌린다.")
            return 1
        print(f"\n{len(keys)}개 단계 전부 관문 통과")

    nxt = h.first_incomplete()
    if nxt:
        print(f"\n다음 할 단계: {nxt.key} — {nxt.name}")
    elif h.meta["status"] == STATUS_OPEN:
        print("\n모든 단계가 끝났는데 status가 '진행중'이다 — 2값 중 하나로 닫아야 한다")
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="사이클 단계 관문 검사")
    ap.add_argument("cycle_dir", type=Path)
    ap.add_argument("--stage", choices=handoff.STAGE_KEYS, default=None)
    args = ap.parse_args()
    try:
        return run(args.cycle_dir, args.stage)
    except handoff.HandoffError as exc:
        print(f"핸드오프 파일 오류:\n{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
