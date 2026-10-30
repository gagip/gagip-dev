#!/usr/bin/env python3
"""2단계 진단의 추출 단계.

  sessions: 기간 안 세션을 레코드(sessions.jsonl)로 뽑고 분류용 묶음(chunks/chunk_NN.md)으로 나눈다.
  context:  1차 분류가 고른 교정 후보마다 원본에서 그 발화·바로 앞 에이전트 응답·그때까지 연 .md 파일을 뽑아
            재판정용 묶음(context/ctx_NN.jsonl)으로 나눈다.

분기 세션(기존 세션을 복제해 이어 간 세션)은 sources.trim_forks 가 fork_of 를 적고 복사된 사건을 지운다.
context 단계는 같은 원래 세션 계열 안에서 같은 교정 인용문을 한 번만 남긴다.
"""

import argparse
import collections
import glob
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sources  # noqa: E402

MAX_MSG, MAX_MSGS = 500, 60
CHUNK_MSG, CHUNK_MSGS = 350, 40
CHUNK_CHARS = 200_000
DEFAULT_EXCLUDE = ("/private/var/folders/", "/private/tmp/", "-private-var-folders-", "-private-tmp-")
MD_PATH_RE = re.compile(r"([^\s\"'`\\]+\.md)(?![\w.-])")


def key(s):
    return f"{s.tool}:{s.id}"


def record(s):
    users = [e for e in s.events if e.kind == "user"]
    tools = collections.Counter(e.name.split("__")[-1] for e in s.events if e.kind == "tool")
    files = collections.Counter()
    for e in s.events:
        if e.kind == "tool" and e.name in ("Write", "Edit", "apply_patch"):
            m = re.search(r'"file_path":\s*"([^"]+)"', e.args) or re.search(r"\*\*\* (?:Update|Add) File: (\S+)", e.args)
            if m:
                files[m.group(1)] += 1
    return dict(
        key=key(s), tool=s.tool, id=s.id, path=s.path, project=s.project, title=s.title,
        start=s.start, end=s.end, compactions=s.compactions, interrupts=s.interrupts,
        user_msgs=len(users), prompts=[dict(ts=e.ts, text=e.text[:MAX_MSG]) for e in users[:MAX_MSGS]],
        skills=dict(collections.Counter(s.skills()).most_common(25)),
        agents=dict(collections.Counter(e.name for e in s.events if e.kind == "agent").most_common(10)),
        tools=dict(tools.most_common(10)), files=list(files)[:10], fork_of=s.fork_of or None,
    )


def render(r):
    head = (f"### {r['key']} | {r['project']} | {r['start'][:16]} ~ {r['end'][:16]} | 제목={r['title'] or '-'}"
            f" | 압축={r['compactions']} 중단={r['interrupts']}" + (f" | 분기={r['fork_of']}" if r["fork_of"] else ""))
    meta = f"스킬={r['skills']} 에이전트={r['agents']}\n도구상위={r['tools']}\n쓴파일={r['files'][:8]}"
    msgs = "\n".join(f"- [{p['ts'][5:16]}] {p['text'][:CHUNK_MSG].replace(chr(10), ' / ')}" for p in r["prompts"][:CHUNK_MSGS])
    return f"{head}\n{meta}\n사용자 발화({r['user_msgs']}개 중 최대 {CHUNK_MSGS}):\n{msgs}\n"


def split(blocks, n):
    """blocks 를 순서대로 글자 수가 비슷한 n 묶음으로."""
    total = sum(map(len, blocks))
    target, out, cur = total / max(n, 1), [], []
    for b in blocks:
        cur.append(b)
        if sum(map(len, cur)) >= target and len(out) < n - 1:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def cmd_sessions(args):
    today = datetime.strptime(args.today, "%Y-%m-%d") if args.today else datetime.now()
    until = args.until or today.strftime("%Y-%m-%d")
    since = args.since or (today - timedelta(days=args.days)).strftime("%Y-%m-%d")
    stats = sources.ScanStats()
    excluded = 0
    records = []
    for s in sources.load_sessions(args.source, since=since, until=until, stats=stats):
        if any(x in s.path or x in (s.project or "") for x in args.exclude):
            excluded += 1
            continue
        r = record(s)
        if r["user_msgs"]:
            records.append(r)
    os.makedirs(os.path.join(args.out_dir, "chunks"), exist_ok=True)
    with open(os.path.join(args.out_dir, "sessions.jsonl"), "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    blocks = [render(r) for r in records]
    n = args.chunks or max(1, math.ceil(sum(map(len, blocks)) / CHUNK_CHARS))
    for f in glob.glob(os.path.join(args.out_dir, "chunks", "chunk_*.md")):
        os.remove(f)
    groups = split(blocks, n) if blocks else []
    for i, c in enumerate(groups, 1):
        with open(os.path.join(args.out_dir, "chunks", f"chunk_{i:02d}.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(c))
    meta = dict(since=since, until=until, source=args.source, sessions=len(records),
                by_tool=dict(collections.Counter(r["tool"] for r in records)),
                forks=sum(1 for r in records if r["fork_of"]), excluded=excluded,
                skipped_zst=stats.skipped_zst, skipped_subagent=stats.skipped_subagent,
                duplicates=stats.duplicates, fork_events_dropped=stats.fork_events_dropped, chunks=len(groups))
    with open(os.path.join(args.out_dir, "extract_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False))


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def find_context(sess, quote):
    """교정 인용문이 나온 사용자 발화와 그 직전 맥락. 못 찾으면 None."""
    k = norm(quote)[:25]
    if not k:
        return None
    ev = sess.events
    idx = next((i for i, e in enumerate(ev) if e.kind == "user" and k in norm(e.text)), None)
    if idx is None:
        return None
    prev = next((i for i in range(idx - 1, -1, -1) if ev[i].kind == "user"), -1)
    between = ev[prev + 1:idx]
    opened = []  # 그 교정 전에 도구로 언급한 .md 경로, 처음 나온 순서
    for e in ev[:idx]:
        if e.kind == "tool":
            for p in MD_PATH_RE.findall(e.args):
                if p not in opened:
                    opened.append(p)
    reply = "\n...\n".join(e.text for e in between if e.kind == "text")
    return dict(
        user_correction=ev[idx].text[:1200],
        previous_user_request=ev[prev].text[:800] if prev >= 0 else "",
        agent_reply_before=reply[-1500:],
        agent_actions_before=[f"{e.kind}: {e.name} {e.args[:100]}".strip() for e in between if e.kind in ("tool", "skill", "agent")][-12:],
        skills_so_far=sorted({e.name for e in ev[:idx] if e.kind == "skill"}),
        md_opened_before=opened[-30:],
        md_opened_all=opened,
    )


def cmd_context(args):
    recs = {}
    with open(os.path.join(args.out_dir, "sessions.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            recs[r["key"]] = r
    classified = []
    for f in sorted(glob.glob(os.path.join(args.out_dir, "classified", "chunk_*.json"))):
        with open(f, encoding="utf-8") as fh:
            classified += json.load(fh)
    classified.sort(key=lambda s: (recs.get(str(s.get("id"))) or {}).get("start", ""))
    def root(sid):
        hops = 0
        while (recs.get(sid) or {}).get("fork_of") and hops < 50:
            sid, hops = recs[sid]["fork_of"], hops + 1
        return sid

    # 분기 세션은 원래 세션의 앞쪽 발화를 복사하므로, 같은 원래 세션 계열 안에서만 같은 인용문을 한 번 센다.
    cands, seen, dup = [], set(), 0
    for s in classified:
        for c in s.get("corrections") or []:
            q = (root(str(s.get("id"))), norm(c.get("quote"))[:40])
            if not q[1]:
                continue
            if q in seen:
                dup += 1
                continue
            seen.add(q)
            cands.append((str(s.get("id")), c))
    cache, out, miss = {}, [], 0
    for n, (sid, c) in enumerate(cands):
        r = recs.get(sid)
        if r is None:
            miss += 1
            continue
        if r["path"] not in cache:
            lines, err = sources.read_lines(r["path"])
            sess = None
            if not err:
                sess = sources.parse_claude(r["path"], lines) if r["tool"] == "claude" else sources.parse_codex(r["path"], lines)
            cache[r["path"]] = sess
        sess = cache[r["path"]]
        ctx = find_context(sess, c.get("quote")) if sess else None
        if ctx is None:
            miss += 1
            continue
        out.append(dict(n=n, session=sid, date=r["start"][:10], title=r["title"], stage=c.get("stage"),
                        quote=c.get("quote"), **ctx))
    d = os.path.join(args.out_dir, "context")
    os.makedirs(d, exist_ok=True)
    for f in glob.glob(os.path.join(d, "ctx_*.jsonl")):
        os.remove(f)
    opened = {r["n"]: r.pop("md_opened_all") for r in out}
    with open(os.path.join(d, "opened.json"), "w", encoding="utf-8") as fh:
        json.dump(opened, fh, ensure_ascii=False)
    parts = min(args.parts or math.ceil(len(out) / 85), len(out))
    size = math.ceil(len(out) / parts) if parts else 0
    for i in range(parts):
        with open(os.path.join(d, f"ctx_{i + 1:02d}.jsonl"), "w", encoding="utf-8") as fh:
            for r in out[i * size:(i + 1) * size]:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    meta = dict(candidates=len(cands), duplicates_removed=dup, matched=len(out), missing=miss, parts=parts)
    with open(os.path.join(args.out_dir, "context_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False))


def main(argv=None):
    p = argparse.ArgumentParser(description="2단계 진단 추출")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("sessions")
    a.add_argument("--out-dir", required=True)
    a.add_argument("--days", type=int, default=30)
    a.add_argument("--since")
    a.add_argument("--until")
    a.add_argument("--today")
    a.add_argument("--source", default="all", choices=("all",) + sources.SOURCES)
    a.add_argument("--chunks", type=int, help="묶음 수 (기본: 20만 자당 하나)")
    a.add_argument("--exclude", nargs="*", default=list(DEFAULT_EXCLUDE), help="경로·작업 폴더에 이 문자열이 있으면 제외 (스킬 평가 임시 세션)")
    b = sub.add_parser("context")
    b.add_argument("--out-dir", required=True)
    b.add_argument("--parts", type=int, help="재판정 묶음 수 (기본: 85건당 하나)")
    args = p.parse_args(argv)
    (cmd_sessions if args.cmd == "sessions" else cmd_context)(args)


if __name__ == "__main__":
    main()
