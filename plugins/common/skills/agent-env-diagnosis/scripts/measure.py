#!/usr/bin/env python3
"""1단계 빠른 측정 — Claude Code·Codex 세션 기록에서 스킬·서브에이전트 사용을 센다.

  - 스킬 도달률: 스킬을 한 번이라도 부른 세션 / 전체 세션
  - 스킬별 호출 수·주간 호출·평균 후속 체인(직후 30개 도구 호출 안에 이어 부른 다른 스킬 수)
  - 묶음 후보: A 직후 처음 나온 다른 스킬 B 의 쌍별 빈도
  - 스킬 스크립트 직접 실행 수: skills/<이름>/scripts/ 를 부른 도구 호출(스킬 호출 0 으로 잡히는 스킬 확인용)

출력은 마크다운(기본 stdout, --out 이면 파일).
"""

import argparse
import collections
import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sources  # noqa: E402

CHAIN_WINDOW = 30
SCRIPT_RE = re.compile(r"skills/([\w.-]+)/scripts/")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="스킬·서브에이전트 사용 지표 (Claude Code·Codex)")
    p.add_argument("--days", type=int, default=14, help="오늘 기준 최근 N일 (기본 14)")
    p.add_argument("--since", help="시작일 YYYY-MM-DD (지정 시 --days 무시)")
    p.add_argument("--until", help="종료일 YYYY-MM-DD (기본 오늘)")
    p.add_argument("--source", default="all", choices=("all",) + sources.SOURCES)
    p.add_argument("--project", help="프로젝트 경로 부분 문자열 필터")
    p.add_argument("--top", type=int, default=15)
    p.add_argument("--out", help="마크다운 저장 경로")
    p.add_argument("--today", help="기준일 YYYY-MM-DD (재현용)")
    return p.parse_args(argv)


def period(args):
    today = datetime.strptime(args.today, "%Y-%m-%d") if args.today else datetime.now()
    until = args.until or today.strftime("%Y-%m-%d")
    since = args.since or (today - timedelta(days=args.days)).strftime("%Y-%m-%d")
    return since, until


def measure(sessions, span_weeks):
    m = dict(
        sessions=len(sessions), by_tool=collections.Counter(s.tool for s in sessions),
        skill_calls=collections.Counter(), skill_sessions=0, agent_sessions=0,
        agent_types=collections.Counter(), chain=collections.defaultdict(list),
        transitions=collections.Counter(), script_calls=collections.Counter(),
        slash=collections.Counter(), by_date=collections.Counter(),
    )
    for s in sessions:
        m["by_date"][s.start[:10]] += 1
        m["slash"].update(s.slash)
        calls = [e for e in s.events if e.kind in ("tool", "skill", "agent")]
        skills = [e.name for e in calls if e.kind == "skill"]
        agents = [e.name for e in calls if e.kind == "agent"]
        m["skill_calls"].update(skills)
        m["agent_types"].update(agents)
        m["skill_sessions"] += bool(skills)
        m["agent_sessions"] += bool(agents)
        m["script_calls"].update({x for e in calls if e.kind == "tool" for x in SCRIPT_RE.findall(e.args)})
        for i, e in enumerate(calls):
            if e.kind != "skill":
                continue
            followers, first, seen_tools = set(), None, 0
            for f in calls[i + 1:]:
                if f.kind == "tool":
                    seen_tools += 1
                    if seen_tools > CHAIN_WINDOW:
                        break
                elif f.kind == "skill" and f.name != e.name:
                    followers.add(f.name)
                    first = first or f.name
            m["chain"][e.name].append(len(followers))
            if first:
                m["transitions"][(e.name, first)] += 1
    m["weekly"] = {k: v / span_weeks for k, v in m["skill_calls"].items()}
    return m


def table(w, head, rows):
    w("| " + " | ".join(head) + " |")
    w("|---" + "|---:" * (len(head) - 1) + "|")
    for r in rows:
        w("| " + " | ".join(str(x) for x in r) + " |")
    w("")


def report(m, since, until, span_days, stats, args):
    out = []
    w = out.append
    n = m["sessions"]
    pct = lambda a: f"{100 * a / n:.0f}%" if n else "-"
    w(f"# 스킬·서브에이전트 사용 지표 — {since} ~ {until} ({span_days}일)")
    w("")
    if stats.skipped_zst:
        w(f"> 주의: zstd 명령이 없어 압축된 Codex 기록 {stats.skipped_zst}개를 읽지 못했다.")
        w("")
    by_tool = ", ".join(f"{k} {v}" for k, v in sorted(m["by_tool"].items())) or "-"
    w(f"- 읽은 기록: {args.source} · 분석 세션 **{n}개** ({by_tool}; 20줄 이하 빈 세션·하위 세션 제외)")
    if args.project:
        w(f"- 프로젝트 필터: `{args.project}`")
    w(f"- 스킬 도달률: **{pct(m['skill_sessions'])}** ({m['skill_sessions']}/{n})")
    w(f"- 서브에이전트 도달률: **{pct(m['agent_sessions'])}** ({m['agent_sessions']}/{n})")
    if stats.unreadable:
        w(f"- 읽지 못한 파일: {stats.unreadable}")
    w("")
    w("## 스킬 호출")
    w("")
    rows = []
    for sk, c in m["skill_calls"].most_common(args.top):
        ch = m["chain"].get(sk) or [0]
        rows.append((f"`{sk}`", c, f"{m['weekly'][sk]:.1f}", f"{sum(ch) / len(ch):.2f}"))
    table(w, ("스킬", "호출", "주간", "평균 후속 체인"), rows)
    w("> Codex 는 스킬 호출이 따로 기록되지 않아, 도구 호출 인자에 나온 `skills/<이름>/SKILL.md` 로 센다.")
    w("> 사용자가 `/이름`으로 직접 연 스킬은 Skill 도구 호출이 없어 이 표와 도달률에 빠지고, 아래 슬래시 커맨드 표에만 나온다.")
    w("")
    w("## 묶음 후보 (A 직후 처음 따라온 B)")
    w("")
    table(w, ("A → B", "횟수"), [(f"`{a}` → `{b}`", c) for (a, b), c in m["transitions"].most_common(args.top)])
    if m["script_calls"]:
        w("## 스킬 스크립트 직접 실행 (세션 수)")
        w("")
        table(w, ("스킬", "세션"), [(f"`{k}`", c) for k, c in m["script_calls"].most_common(args.top)])
    if m["agent_types"]:
        w("## 서브에이전트 종류")
        w("")
        table(w, ("종류", "호출"), [(f"`{k}`", c) for k, c in m["agent_types"].most_common(args.top)])
    w("## 일별 세션")
    w("")
    table(w, ("날짜", "세션"), [(d, m["by_date"][d]) for d in sorted(m["by_date"])])
    if m["slash"]:
        w("## 슬래시 커맨드 입력")
        w("")
        table(w, ("커맨드", "입력"), [(f"`/{k}`", c) for k, c in m["slash"].most_common(args.top)])
    return "\n".join(out)


def main(argv=None):
    args = parse_args(argv)
    since, until = period(args)
    span_days = (datetime.strptime(until, "%Y-%m-%d") - datetime.strptime(since, "%Y-%m-%d")).days + 1
    stats = sources.ScanStats()
    sessions = sources.load_sessions(args.source, since=since, until=until, project=args.project, stats=stats)
    m = measure(sessions, max(span_days / 7.0, 1e-9))
    text = report(m, since, until, span_days, stats, args)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"saved: {args.out} ({m['sessions']} sessions)")
    else:
        print(text)


if __name__ == "__main__":
    main()
