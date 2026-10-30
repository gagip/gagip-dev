#!/usr/bin/env python3
"""에이전트 환경 자산이 얼마나 실리고 읽히는지 센다.

  - 상시 지침(--always): 매 세션 자동으로 실리는 파일의 바이트·규칙 줄 수
  - 상세 파일(--details 폴더): 파일마다 그 파일을 도구로 연 세션 수
  - 메모리(--memory 폴더): 파일마다 연 세션 수, 기간 동안 한 번도 안 열린 파일
  - 훅: 설정된 훅 수(--hooks 파일)와 기록에 남은 발동 수(hookName·첨부 종류별)

"열었다"는 그 세션의 도구 호출 인자에 `<부모 폴더 이름>/<파일 이름>` 이 나온 것이다.
고치려고 연 경우도 들어가고, 셸 명령 안의 경로도 잡힌다.
"""

import argparse
import collections
import json
import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sources  # noqa: E402

RULE_LINE_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+\S")
PATH_PART_RE = re.compile(r"([^\s/\"'\\`]+)/([^\s/\"'\\`]+)/([^\s/\"'\\`]+\.md)(?![\w.-])")


def default_always():
    files = [os.path.join(sources.claude_home(), "CLAUDE.md"), os.path.join(sources.codex_home(), "AGENTS.md")]
    return [f for f in files if os.path.isfile(f)]


def default_memory():
    try:
        with open(os.path.join(sources.claude_home(), "settings.json"), encoding="utf-8") as fh:
            d = json.load(fh).get("autoMemoryDirectory")
    except (OSError, json.JSONDecodeError):
        return None
    return os.path.expanduser(d) if d else None


def default_hooks():
    files = [os.path.join(sources.claude_home(), "settings.json"), os.path.join(sources.codex_home(), "hooks.json")]
    return [f for f in files if os.path.isfile(f)]


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="에이전트 환경 자산 크기·열람 수")
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--since")
    p.add_argument("--until")
    p.add_argument("--today")
    p.add_argument("--source", default="all", choices=("all",) + sources.SOURCES)
    p.add_argument("--always", nargs="*", help="매 세션 자동으로 실리는 지침 파일 (기본: 두 도구의 전역 지침)")
    p.add_argument("--details", nargs="*", default=[], help="필요할 때 읽는 상세 파일 폴더")
    p.add_argument("--memory", help="메모리 폴더 (기본: Claude settings.json 의 autoMemoryDirectory)")
    p.add_argument("--hooks", nargs="*", help="훅 설정 파일 (기본: Claude settings.json, Codex hooks.json)")
    p.add_argument("--top", type=int, default=15)
    p.add_argument("--json", help="집계 JSON 저장 경로 (2단계 aggregate.py 입력)")
    p.add_argument("--out", help="마크다운 저장 경로")
    return p.parse_args(argv)


def md_files(folder):
    """폴더 바로 아래 .md 파일 (하위 폴더 = 보관함은 빼고)."""
    if not folder or not os.path.isdir(folder):
        return []
    return sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".md"))


def key_of(path):
    """경로 끝 세 마디. 다른 프로젝트의 같은 이름 폴더(memory/MEMORY.md 등)와 섞이지 않게 한다."""
    return "/".join(os.path.normpath(path).split(os.sep)[-3:])


def opened_sessions(sessions, paths):
    """경로마다 그 경로를 도구 인자에서 언급한 세션 수."""
    by_key = collections.defaultdict(list)
    for p in paths:
        by_key[key_of(p)].append(p)
    count = collections.Counter()
    for s in sessions:
        args = "\n".join(e.args for e in s.events if e.kind == "tool")
        keys = {"/".join(m) for m in PATH_PART_RE.findall(args)}
        count.update(p for k in keys & by_key.keys() for p in by_key[k])
    return count


def always_info(paths):
    seen, rows = set(), []
    for p in paths:
        real = os.path.realpath(p)
        if real in seen or not os.path.isfile(real):
            continue
        seen.add(real)
        with open(real, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        rows.append(dict(path=p, real=real, bytes=len(text.encode("utf-8")),
                         rule_lines=sum(1 for l in text.splitlines() if RULE_LINE_RE.match(l))))
    return rows


def configured_hooks(paths):
    out = collections.Counter()
    for p in paths:
        try:
            with open(p, encoding="utf-8") as fh:
                hooks = json.load(fh).get("hooks") or {}
        except (OSError, json.JSONDecodeError):
            continue
        for ev, entries in hooks.items():
            out[(os.path.basename(os.path.dirname(p)) + "/" + os.path.basename(p), ev)] += len(entries or [])
    return out


def scan(sessions, always, details, memory, hooks):
    detail_files = [f for d in details for f in md_files(d)]
    memory_files = md_files(memory)
    det = opened_sessions(sessions, detail_files)
    mem = opened_sessions(sessions, memory_files)
    fired, fired_sessions = collections.Counter(), collections.Counter()
    for s in sessions:
        fired.update(s.hooks)
        fired_sessions.update(set(s.hooks))
    return dict(
        sessions=len(sessions), by_tool=dict(collections.Counter(s.tool for s in sessions)),
        always=always_info(always),
        details=[dict(file=f, opened_sessions=det[f]) for f in detail_files],
        memory_dir=memory, memory=[dict(file=f, opened_sessions=mem[f]) for f in memory_files],
        hooks_configured=[dict(file=k[0], event=k[1], entries=v) for k, v in sorted(configured_hooks(hooks).items())],
        hooks_fired=[dict(hook=k[0], kind=k[1], count=v, sessions=fired_sessions[k]) for k, v in fired.most_common()],
    )


def report(r, since, until, top):
    out = []
    w = out.append
    w(f"# 에이전트 환경 자산 — {since} ~ {until}")
    w("")
    if r.get("skipped_zst"):
        w(f"> 주의: zstd 명령이 없어 압축된 Codex 기록 {r['skipped_zst']}개를 읽지 못했다.")
        w("")
    w(f"- 분석 세션 {r['sessions']}개 ({', '.join(f'{k} {v}' for k, v in sorted(r['by_tool'].items()))})")
    w("")
    w("## 상시 지침 (매 세션 자동으로 실림)")
    w("")
    w("| 파일 | 바이트 | 규칙 줄 |")
    w("|---|---:|---:|")
    for a in r["always"]:
        w(f"| `{a['path']}` | {a['bytes']:,} | {a['rule_lines']} |")
    w(f"| 합계 | {sum(a['bytes'] for a in r['always']):,} | {sum(a['rule_lines'] for a in r['always'])} |")
    w("")
    if r["details"]:
        w("## 상세 파일 (필요할 때 읽음) — 연 세션 수")
        w("")
        w("| 파일 | 연 세션 |")
        w("|---|---:|")
        for d in sorted(r["details"], key=lambda d: -d["opened_sessions"]):
            w(f"| `{key_of(d['file'])}` | {d['opened_sessions']} |")
        w("")
    if r["memory"]:
        never = [m for m in r["memory"] if not m["opened_sessions"]]
        w(f"## 메모리 — 파일 {len(r['memory'])}개 중 기간 동안 안 열린 파일 {len(never)}개 ({100 * len(never) / len(r['memory']):.0f}%)")
        w("")
        w("| 많이 열린 파일 | 연 세션 |")
        w("|---|---:|")
        for m in sorted(r["memory"], key=lambda m: -m["opened_sessions"])[:top]:
            w(f"| `{os.path.basename(m['file'])}` | {m['opened_sessions']} |")
        w("")
        w("목록 파일(MEMORY.md 등)이 매 세션 자동으로 실리면 한 줄 요약만으로 쓰였을 수 있다. 안 열린 것이 곧 쓸모없다는 뜻은 아니다.")
        w("")
    w("## 훅")
    w("")
    w("| 설정 파일 | 이벤트 | matcher 묶음 |")
    w("|---|---|---:|")
    for h in r["hooks_configured"]:
        w(f"| `{h['file']}` | {h['event']} | {h['entries']} |")
    w("")
    if r["hooks_fired"]:
        w("| 기록에 남은 발동 (Claude) | 종류 | 횟수 | 세션 |")
        w("|---|---|---:|---:|")
        for h in r["hooks_fired"][:top]:
            w(f"| `{h['hook']}` | {h['kind']} | {h['count']} | {h['sessions']} |")
        w("")
        w("발동 기록에는 사용자가 설정한 훅과 앱·플러그인이 넣은 안내가 섞인다. 내용은 기록 원문에서 확인한다.")
        w("")
    return "\n".join(out)


def main(argv=None):
    args = parse_args(argv)
    today = datetime.strptime(args.today, "%Y-%m-%d") if args.today else datetime.now()
    until = args.until or today.strftime("%Y-%m-%d")
    since = args.since or (today - timedelta(days=args.days)).strftime("%Y-%m-%d")
    stats = sources.ScanStats()
    sessions = sources.load_sessions(args.source, since=since, until=until, stats=stats)
    r = scan(sessions,
             args.always if args.always is not None else default_always(),
             args.details, args.memory or default_memory(),
             args.hooks if args.hooks is not None else default_hooks())
    r.update(since=since, until=until, skipped_zst=stats.skipped_zst)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(r, fh, ensure_ascii=False, indent=1)
    text = report(r, since, until, args.top)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"saved: {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
