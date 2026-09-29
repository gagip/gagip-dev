"""사이클 상태 조회와 검증 후 전이. 실제 구현·git 변경·push는 실행하지 않는다."""

from __future__ import annotations

import argparse
import fcntl
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

import gate
import handoff
import mdsec
import paths
from handoff import STATE_DONE, STATE_SKIPPED, STATE_TODO
from handoff import STATUS_DONE, STATUS_IMPOSSIBLE, STATUS_OPEN


class TransitionError(Exception):
    """상태를 바꾸지 않고 호출자에게 복구할 이유를 돌려준다."""


CYCLE_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[^/]+$")


def init(cycle_dir: Path, title: str, plan: str | None = None) -> handoff.Handoff:
    """템플릿으로 새 사이클을 만든다. 폴더 이름이 곧 cycle_id다.

    폴더 이름의 날짜는 옛 형식 사이클을 가르는 기준이라 형식을 강제한다. `plan`은 실행 위치와
    무관하게 같은 파일을 가리키도록 절대경로로 풀어 저장한다.
    """
    target = Path(cycle_dir).expanduser().resolve()
    if not CYCLE_ID_RE.match(target.name):
        raise TransitionError(f"사이클 폴더 이름은 YYYY-MM-DD_주제 형식이어야 한다: {target.name}")
    if target.exists():
        raise TransitionError(f"이미 있는 사이클 폴더다: {target}")
    if not title.strip() or "\n" in title:
        raise TransitionError("제목은 비어 있지 않은 한 줄이어야 한다")
    plan_value = ""
    if plan:
        plan_path = Path(plan).expanduser().resolve()
        if not plan_path.is_file():
            raise TransitionError(f"계획서 파일이 없다: {plan_path}")
        plan_value = str(plan_path)
    text = paths.TEMPLATE_HANDOFF.read_text(encoding="utf-8")
    for key, value in (("cycle_id", target.name), ("title", title.strip()),
                       ("opened", date.today().isoformat()), ("plan", plan_value)):
        text = handoff.set_meta(text, key, value)
    text = text.replace("# 사이클: (제목)", f"# 사이클: {title.strip()}", 1)
    target.mkdir(parents=True)
    (target / handoff.HANDOFF_FILENAME).write_text(text, encoding="utf-8")
    return handoff.load(target)


def mode(h: handoff.Handoff) -> str:
    value = h.meta.get("mode", "draft")
    if value not in ("draft", "auto"):
        raise TransitionError("mode는 draft 또는 auto여야 한다")
    return value


def validate_state(h: handoff.Handoff) -> None:
    current_mode = mode(h)
    pending = False
    for row in h.stages:
        if row.state == STATE_TODO:
            pending = True
        elif row.state == STATE_DONE and pending:
            raise TransitionError(f"{row.key}: 앞에 미완 단계가 있다")
        elif row.state == STATE_SKIPPED and current_mode == "auto":
            raise TransitionError("auto 모드에서는 ship을 생략할 수 없다")
    if h.meta["status"] == STATUS_DONE and h.first_incomplete():
        raise TransitionError("달성으로 기록됐지만 미완 단계가 있다")
    if h.meta["status"] == STATUS_OPEN and h.stage("close").state == STATE_DONE:
        raise TransitionError("close가 완료됐지만 종결값이 진행중이다")


def verify(h: handoff.Handoff, key: str, *, at_transition: bool = False) -> None:
    ok, reasons = gate.check_stage(h, key, at_transition=at_transition)
    if not ok:
        raise TransitionError(f"{key}: " + " / ".join(reasons))


def verify_completed(h: handoff.Handoff) -> None:
    for row in h.stages:
        if row.state == STATE_DONE:
            verify(h, row.key)


def verify_commits(h: handoff.Handoff) -> None:
    ok, reasons = gate.check_commits(h)
    if not ok:
        raise TransitionError("커밋 검사: " + " / ".join(reasons))


def inspect(cycle_dir: Path) -> handoff.Handoff:
    h = handoff.load(cycle_dir)
    validate_state(h)
    if h.meta["status"] != STATUS_IMPOSSIBLE:
        verify_completed(h)
        current = h.first_incomplete()
        if current and current.key in ("ship", "close"):
            verify_commits(h)
    return h


def replace_section(text: str, title: str, update) -> str:
    span = mdsec.section_span(text, title)
    if span is None:
        raise TransitionError(f"## {title} 절이 없다")
    start, end = span
    return text[:start] + update(text[start:end]) + text[end:]


def render(original: str, h: handoff.Handoff, decision: str, action: str) -> str:
    if not decision.strip() or len(decision.splitlines()) != 1:
        raise TransitionError("결정 근거는 비어 있지 않은 한 줄이어야 한다")
    entry = f"- {date.today().isoformat()} · {action} · {decision.strip()}"
    if len(entry) > handoff.DECISION_LOG_MAX:
        raise TransitionError(f"결정 로그는 {handoff.DECISION_LOG_MAX}자 이내여야 한다")

    front, body = original[4:].split("\n---\n", 1)
    for key in ("status", "mode"):
        if key not in h.meta:
            continue
        replacement = f"{key}: {h.meta[key]}"
        front, count = re.subn(rf"^{key}:.*$", lambda _: replacement, front,
                              count=1, flags=re.MULTILINE)
        if not count:
            front += "\n" + replacement
    text = "---\n" + front + "\n---\n" + body

    def update_rows(section: str) -> str:
        for row in h.stages:
            pattern = rf"^[ \t]*\|\s*{row.key}\s*\|[^|\n]*\|[^|\n]*\|[ \t]*$"
            replacement = f"| {row.key} | {row.state} | {row.artifact} |"
            section, count = re.subn(pattern, lambda _: replacement, section,
                                    count=1, flags=re.MULTILINE)
            if count != 1:
                raise TransitionError(f"진행 표의 {row.key} 행을 갱신할 수 없다")
        return section

    text = replace_section(text, "진행", update_rows)
    return replace_section(text, "결정 로그", lambda s: s.rstrip() + "\n\n" + entry + "\n\n")


def artifact_path(h: handoff.Handoff, raw: str) -> str:
    if raw != raw.strip():
        raise TransitionError("산출물 경로의 앞뒤에는 공백을 넣을 수 없다")
    path = Path(raw)
    resolved = (h.cycle_dir / path).resolve()
    if path.is_absolute() or not resolved.is_relative_to(h.cycle_dir.resolve()):
        raise TransitionError("산출물은 사이클 폴더 안의 상대경로여야 한다")
    if not raw or any(c in raw for c in "|\r\n") or not resolved.is_file():
        raise TransitionError("산출물은 실제 파일이어야 하고 표 구분자·개행을 포함할 수 없다")
    if resolved == h.path.resolve():
        raise TransitionError("handoff.md 자체를 단계 산출물로 쓸 수 없다")
    return str(path)


def save(h: handoff.Handoff, original: bytes, updated: str) -> None:
    candidate = handoff.parse(updated, h.path)
    validate_state(candidate)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=h.cycle_dir, prefix=".handoff-", delete=False) as f:
            tmp_path = Path(f.name)
            os.fchmod(f.fileno(), h.path.stat().st_mode & 0o777)
            f.write(updated.encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        if h.path.is_symlink() or h.path.read_bytes() != original:
            raise TransitionError("검증 중 handoff.md가 변경됐다 — 다시 조회한다")
        os.replace(tmp_path, h.path)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def transition(cycle_dir: Path, action: str, *, stage: str | None = None,
               artifact: str = "", decision: str, new_mode: str | None = None) -> handoff.Handoff:
    directory = Path(cycle_dir).resolve()
    fd = os.open(directory, os.O_RDONLY)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise TransitionError("같은 사이클의 다른 상태 변경이 진행 중이다") from None
        path = directory / handoff.HANDOFF_FILENAME
        if path.is_symlink():
            raise TransitionError("handoff.md 심볼릭 링크는 상태 변경 대상으로 지원하지 않는다")
        original = path.read_bytes()
        h = handoff.parse(original.decode("utf-8"), path)
        validate_state(h)
        if h.meta["status"] != STATUS_OPEN:
            raise TransitionError("이미 종결된 사이클은 변경할 수 없다")

        if action == "stop":
            h.meta["status"] = STATUS_IMPOSSIBLE
        elif action == "mode":
            if new_mode not in ("draft", "auto"):
                raise TransitionError("mode는 draft 또는 auto여야 한다")
            if h.stage("ship").state != STATE_TODO:
                raise TransitionError("ship이 이미 처리되어 모드를 바꿀 수 없다")
            h.meta["mode"] = new_mode
        elif action in ("complete", "skip"):
            current = h.first_incomplete()
            if current is None or current.key != stage:
                raise TransitionError(f"현재 단계만 처리할 수 있다 — 현재: {current.key if current else '없음'}")
            verify_completed(h)
            if action == "skip":
                if stage not in handoff.SKIPPABLE_KEYS or mode(h) != "draft":
                    raise TransitionError("초안 모드의 ship만 생략할 수 있다")
                verify_commits(h)
                current.state = STATE_SKIPPED
                current.artifact = ""
            else:
                if stage == "ship" and mode(h) != "auto":
                    raise TransitionError("ship 실행은 명시적으로 요청된 auto 모드에서만 가능하다")
                current.artifact = artifact_path(h, artifact)
                current.state = STATE_DONE
                if stage == "close":
                    h.meta["status"] = STATUS_DONE
                verify(h, stage, at_transition=True)
        else:
            raise TransitionError(f"지원하지 않는 상태 변경: {action}")
        validate_state(h)
        label = f"{action} {stage or new_mode or ''}".strip()
        updated = render(original.decode("utf-8"), h, decision, label)
        save(h, original, updated)
        return h
    finally:
        os.close(fd)


def show(h: handoff.Handoff) -> None:
    print(f"사이클: {h.meta['cycle_id']} — {h.meta['title']}")
    print(f"상태: {h.meta['status']} / 모드: {mode(h)}")
    if h.meta["status"] != STATUS_OPEN:
        print("종결된 사이클 — 다음 단계 없음")
    elif current := h.first_incomplete():
        print(f"다음 할 단계: {current.key} — {current.name}")
        if current.key == "ship" and mode(h) == "draft":
            print("초안 모드 — 제출하지 않고 skip ship으로 기록한다")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cycle_dir", type=Path)
    commands = ap.add_subparsers(dest="action", required=True)
    commands.add_parser("status", help="상태와 완료 단계 실물 검증 (읽기 전용)")
    create = commands.add_parser("init", help="템플릿으로 새 사이클 폴더를 만든다")
    create.add_argument("--title", required=True)
    create.add_argument("--plan", help="승인된 계획서(또는 디자인 인계 명세) 파일 경로")
    complete = commands.add_parser("complete", help="검증 성공 후 현재 단계 완료")
    complete.add_argument("stage", choices=handoff.STAGE_KEYS)
    complete.add_argument("--artifact", required=True)
    skip = commands.add_parser("skip", help="초안의 제출 단계 생략")
    skip.add_argument("stage", choices=sorted(handoff.SKIPPABLE_KEYS))
    commands.add_parser("stop", help="사용자가 불가능으로 판단한 근거를 기록하고 종결")
    select_mode = commands.add_parser("mode", help="제출 모드 기록 (실행 권한을 부여하지 않음)")
    select_mode.add_argument("new_mode", choices=("draft", "auto"))
    for parser in (complete, skip, commands.choices["stop"], select_mode):
        parser.add_argument("--decision", required=True, help="무엇을·왜·누가 정했는지 한 줄")
    args = ap.parse_args()
    try:
        if args.action == "status":
            h = inspect(args.cycle_dir)
        elif args.action == "init":
            h = init(args.cycle_dir, args.title, args.plan)
        else:
            h = transition(args.cycle_dir, args.action, stage=getattr(args, "stage", None),
                           artifact=getattr(args, "artifact", ""), decision=args.decision,
                           new_mode=getattr(args, "new_mode", None))
        show(h)
        return 0
    except (TransitionError, handoff.HandoffError, OSError, UnicodeError) as exc:
        print(f"상태 처리 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
