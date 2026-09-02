#!/usr/bin/env python3
"""여러 코딩 에이전트 하네스의 세션 로그를 한 번에 뒤져 과거 대화를 찾는다.

한 프로젝트를 여러 하네스로 번갈아 작업하면 대화 기록이 각자 폴더로 갈라진다.
한쪽만 뒤지면 "그런 얘기 없었다"는 잘못된 결론이 나오므로 양쪽을 함께 훑는다.

  python3 search-sessions.py "키워드" [키워드2 ...] [--days 30]

찾는 곳(있는 것만 훑고, 없는 쪽은 건너뛴 사실을 결과에 밝힌다):
  Claude Code : ~/.claude/projects/**/*.jsonl        (서브에이전트 기록 포함)
  Codex       : ~/.codex/sessions/**/rollout-*.jsonl
                ~/.codex/archived_sessions/*.jsonl
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

HOME = os.path.expanduser("~")
ALL_ROOTS = [
    ("claude", os.path.join(HOME, ".claude", "projects")),
    ("codex", os.path.join(HOME, ".codex", "sessions")),
    ("codex", os.path.join(HOME, ".codex", "archived_sessions")),
]


def parse_ts(value):
    """ISO8601(대개 UTC Z) 문자열을 로컬 시간 datetime으로. 실패하면 None."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return None


def candidate_files(roots, term, days):
    """grep -rl로 후보 파일만 추린다 — 로그 전량 JSON 파싱(수 GB)을 피하는 1차 필터."""
    cutoff = datetime.now().timestamp() - days * 86400 if days else None
    out = []
    for tool, root in roots:
        try:
            res = subprocess.run(
                ["grep", "-rlIiF", "--include=*.jsonl", "--", term, root],
                capture_output=True, text=True,
            )
        except FileNotFoundError:
            sys.exit("grep을 찾을 수 없다.")
        for path in res.stdout.splitlines():
            if cutoff and os.path.getmtime(path) < cutoff:
                continue
            out.append((tool, path))
    return out


def flatten(content):
    """하네스마다 다른 content(문자열 | 블록 리스트)를 평문으로."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and isinstance(block.get("text"), str):
            parts.append(block["text"])
    return "\n".join(parts)


def read_claude(path):
    """(ts, role, text, cwd, session_id) 레코드를 뽑는다."""
    session_id = os.path.splitext(os.path.basename(path))[0]
    cwd = ""
    for line in open(path, errors="replace"):
        if '"type"' not in line:
            continue
        try:
            rec = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        cwd = rec.get("cwd") or cwd
        kind = rec.get("type")
        if kind not in ("user", "assistant"):
            continue
        text = flatten((rec.get("message") or {}).get("content"))
        if text:
            yield parse_ts(rec.get("timestamp")), kind, text, cwd, session_id


def read_codex(path):
    session_id = ""
    cwd = ""
    for line in open(path, errors="replace"):
        if '"type"' not in line:
            continue
        try:
            rec = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        payload = rec.get("payload") or {}
        kind = payload.get("type")
        ts = parse_ts(rec.get("timestamp"))
        if rec.get("type") == "session_meta":
            session_id = payload.get("session_id") or session_id
            cwd = (payload.get("cwd") or cwd).replace("file://", "")
            continue
        if kind == "item_completed":
            item = payload.get("item") or {}
            role = {"UserMessage": "user", "AssistantMessage": "assistant"}.get(item.get("type"))
            if role:
                text = flatten(item.get("content"))
                if text:
                    yield ts, role, text, cwd, session_id
        elif kind == "task_complete":
            text = payload.get("last_agent_message") or ""
            if text:
                yield ts, "assistant", text, cwd, session_id
        elif kind == "agent_message":
            text = flatten(payload.get("content"))
            if text:
                yield ts, "assistant", text, cwd, session_id


def snippet(text, term, width):
    idx = text.lower().find(term.lower())
    if idx < 0:
        idx = 0
    start = max(0, idx - width // 2)
    end = min(len(text), idx + len(term) + width // 2)
    body = " ".join(text[start:end].split())
    return ("…" if start else "") + body + ("…" if end < len(text) else "")


def main():
    ap = argparse.ArgumentParser(description="여러 하네스의 세션 로그를 한 번에 검색한다")
    ap.add_argument("terms", nargs="+", help="검색어(여러 개면 모두 포함된 발화만)")
    ap.add_argument("--days", type=int, default=0, help="최근 N일로 제한(기본 전체)")
    ap.add_argument("--tool", choices=["all", "claude", "codex"], default="all")
    ap.add_argument("--role", choices=["all", "user", "assistant"], default="all")
    ap.add_argument("--project", default="", help="작업 디렉터리 경로에 이 문자열이 든 세션만")
    ap.add_argument("--context", type=int, default=200, help="발췌 길이(글자)")
    ap.add_argument("--max-per-session", type=int, default=3)
    ap.add_argument("--files-only", action="store_true", help="세션 파일 목록만 출력")
    args = ap.parse_args()

    wanted = [(t, r) for t, r in ALL_ROOTS if args.tool in ("all", t)]
    roots = [(t, r) for t, r in wanted if os.path.isdir(r)]
    missing = [r for t, r in wanted if not os.path.isdir(r)]
    if not roots:
        sys.exit("훑을 세션 로그 폴더가 없다: " + ", ".join(missing))

    terms_lower = [t.lower() for t in args.terms]
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days) if args.days else None

    sessions = {}
    for tool, path in candidate_files(roots, args.terms[0], args.days):
        reader = read_claude if tool == "claude" else read_codex
        try:
            records = list(reader(path))
        except OSError:
            continue
        hits = []
        for ts, role, text, cwd, session_id in records:
            if args.role != "all" and role != args.role:
                continue
            if args.project and args.project not in (cwd or ""):
                continue
            if cutoff and ts and ts < cutoff:
                continue
            low = text.lower()
            if not all(t in low for t in terms_lower):
                continue
            hits.append((ts, role, text, cwd, session_id))
        if hits:
            sessions[path] = (tool, hits)

    scanned = "훑은 곳: " + ", ".join(r for _, r in roots)
    if missing:
        scanned += " (없어서 건너뜀: " + ", ".join(missing) + ")"

    if not sessions:
        print("일치하는 대화가 없다.")
        print(scanned)
        print("검색어를 줄여도 0건이면 로그 형식이 바뀌었을 수 있다 — --files-only로 후보 파일이 잡히는지 확인한다.")
        return

    def sort_key(item):
        _, (_, hits) = item
        stamps = [h[0] for h in hits if h[0]]
        return max(stamps) if stamps else datetime.min.replace(tzinfo=timezone.utc)

    total = 0
    for path, (tool, hits) in sorted(sessions.items(), key=sort_key):
        if args.files_only:
            print(f"[{tool}] {path}")
            continue
        stamps = [h[0] for h in hits if h[0]]
        when = max(stamps).strftime("%Y-%m-%d %H:%M") if stamps else "시각 미상"
        cwd = next((h[3] for h in hits if h[3]), "") or "(작업 디렉터리 미상)"
        print(f"\n[{tool}] {when}  {cwd}")
        print(f"  {path}")
        for ts, role, text, _, _ in hits[: args.max_per_session]:
            stamp = ts.strftime("%m-%d %H:%M") if ts else "  --  "
            print(f"  {stamp} {role:<9} {snippet(text, args.terms[0], args.context)}")
        if len(hits) > args.max_per_session:
            print(f"  … 이 세션에 {len(hits) - args.max_per_session}건 더")
        total += len(hits)

    print(f"\n세션 {len(sessions)}개 · 발화 {total}건")
    print(scanned)


if __name__ == "__main__":
    main()
