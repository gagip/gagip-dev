#!/usr/bin/env python3
"""
skill-metrics — Claude Code 세션 JSONL에서 스킬/워크플로우 사용 지표를 집계한다.

두 축의 지표를 한 번에 산출한다:
  ① AutoScore        — 자동화 우선순위 점수 = 주간호출수 × 평균후속체인길이 × (1 + 마찰율)
  ③ 상시 지표(Reach) — 도달률·스킬별 빈도·일별 분포
                       (도달률 = 스킬 미사용 세션의 역수 → 거시적 "미활용" 신호)

출력: 사람이 읽는 마크다운 리포트(기본 stdout, --out 으로 파일 저장).
계산의 근거가 되는 raw 카운트도 함께 낸다.

주의(계약): 세션 파일은 프로세스 경계(외부 파일)다. 깨진 라인/누락 필드는
예외로 죽이지 않고 건너뛴 뒤 끝에 skipped 수를 보고한다.
"""

import argparse
import collections
import json
import os
import re
import sys
from datetime import datetime, timedelta

PROJECTS_DIR = os.path.expanduser("~/.claude/projects")
MIN_LINES = 20            # 이보다 짧은 세션은 즉시 종료/취소된 빈 세션 → 제외
CHAIN_WINDOW = 30         # 한 스킬 호출 직후 이 개수의 tool_use 안에 오는 스킬을 "후속 체인"으로 본다

# ── ① 마찰 신호: 사용자 발화에서 재작업/교정/실패를 나타내는 표현 ──────────────
# 휴리스틱이다. 명백한 교정·재시도·실패만 보수적으로 잡는다(질문성 "왜?"는 제외).
FRICTION_PATTERNS = [
    r"다시\s*해", r"다시\s*만들", r"다시\s*해봐", r"다시\s*돌려",
    r"그게\s*아니", r"그건\s*아니", r"아니라\b", r"아니야", r"틀렸", r"잘못",
    r"안\s*돼", r"안돼", r"안\s*되는", r"안되는",
    r"또\s+실패", r"또\s+에러", r"또\s+안", r"재시도",
    r"\bretry\b", r"\bwrong\b", r"\bnot\s+working\b", r"that'?s\s+not",
]
FRICTION_RE = re.compile("|".join(FRICTION_PATTERNS), re.IGNORECASE)


def parse_args():
    p = argparse.ArgumentParser(description="Claude Code 스킬 사용 지표 집계")
    p.add_argument("--days", type=int, default=14, help="오늘 기준 최근 N일 (기본 14)")
    p.add_argument("--since", help="시작일 YYYY-MM-DD (지정 시 --days 무시)")
    p.add_argument("--until", help="종료일 YYYY-MM-DD (기본: 오늘)")
    p.add_argument("--project", help="프로젝트 경로 부분문자열 필터 (예: myproject)")
    p.add_argument("--top", type=int, default=15, help="랭킹 표 상위 N개 (기본 15)")
    p.add_argument("--out", help="마크다운 저장 경로 (미지정 시 stdout)")
    p.add_argument("--today", help="기준일 주입 YYYY-MM-DD (테스트/재현용; 기본 시스템 날짜)")
    return p.parse_args()


def first_timestamp(path):
    """세션의 첫 timestamp(날짜)를 반환. 없으면 None."""
    try:
        with open(path, errors="ignore") as fh:
            for line in fh:
                m = re.search(r'"timestamp":"(\d{4}-\d{2}-\d{2})', line)
                if m:
                    return m.group(1)
    except OSError:
        return None
    return None


def collect_sessions(since, until, project):
    """기간 내 실질 세션 경로 목록을 (date, path) 로 반환."""
    sessions = []
    if not os.path.isdir(PROJECTS_DIR):
        return sessions
    for root, dirs, files in os.walk(PROJECTS_DIR):
        if "subagents" in root.split(os.sep):
            continue
        for fn in files:
            if not fn.endswith(".jsonl"):
                continue
            path = os.path.join(root, fn)
            if project and project not in path:
                continue
            # 줄 수 필터(빈 세션 제외)
            try:
                with open(path, errors="ignore") as fh:
                    nlines = sum(1 for _ in fh)
            except OSError:
                continue
            if nlines <= MIN_LINES:
                continue
            date = first_timestamp(path)
            if not date or date < since or date > until:
                continue
            sessions.append((date, path))
    sessions.sort()
    return sessions


def extract_events(path):
    """세션을 시간순으로 훑어 (tool_events, user_texts, skipped) 반환.
    tool_events: [{'tool': name, 'skill': skillname|None, 'bash': command|None}, ...]
    """
    tool_events = []
    user_texts = []
    skipped = 0
    try:
        fh = open(path, errors="ignore")
    except OSError:
        return tool_events, user_texts, 1
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            msg = obj.get("message")
            if not isinstance(msg, dict):
                continue
            content = msg.get("content")
            if obj.get("type") == "user":
                text = None
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = " ".join(
                        b.get("text", "") for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                if text and text.strip():
                    user_texts.append(text.strip())
                continue
            if obj.get("type") != "assistant" or not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = block.get("name", "?")
                inp = block.get("input", {}) or {}
                ev = {"tool": name, "skill": None}
                if name == "Skill":
                    ev["skill"] = inp.get("skill", "?")
                tool_events.append(ev)
    return tool_events, user_texts, skipped


def main():
    args = parse_args()
    if args.today:
        today = datetime.strptime(args.today, "%Y-%m-%d")
    else:
        today = datetime.now()
    until = args.until or today.strftime("%Y-%m-%d")
    if args.since:
        since = args.since
    else:
        since = (today - timedelta(days=args.days)).strftime("%Y-%m-%d")

    span_days = (datetime.strptime(until, "%Y-%m-%d") - datetime.strptime(since, "%Y-%m-%d")).days + 1
    span_weeks = max(span_days / 7.0, 1e-9)

    sessions = collect_sessions(since, until, args.project)

    total_sessions = len(sessions)
    skill_calls = collections.Counter()          # 스킬별 총 호출수
    slash_cmds = collections.Counter()           # <command-name> (참고용)
    sessions_with_skill = 0
    sessions_with_agent = 0
    by_date = collections.Counter()
    tool_totals = collections.Counter()

    # ① 체인/마찰용
    chain_len_samples = collections.defaultdict(list)   # skill -> [후속 고유 스킬 수, ...]
    transitions = collections.Counter()                 # (A, B) A 직후 윈도우 내 B
    friction_sessions = collections.defaultdict(lambda: [0, 0])  # skill -> [마찰세션수, 등장세션수]

    total_skipped = 0

    for date, path in sessions:
        by_date[date] += 1
        events, user_texts, skipped = extract_events(path)
        total_skipped += skipped

        session_skills = set()
        has_agent = False
        for ev in events:
            tool_totals[ev["tool"]] += 1
            if ev["skill"]:
                skill_calls[ev["skill"]] += 1
                session_skills.add(ev["skill"])
            if ev["tool"] == "Agent":
                has_agent = True
        if session_skills:
            sessions_with_skill += 1
        if has_agent:
            sessions_with_agent += 1

        # 체인: 스킬 호출 위치마다 윈도우 내 다른 스킬 수집
        skill_positions = [(i, ev["skill"]) for i, ev in enumerate(events) if ev["skill"]]
        for idx, (i, sk) in enumerate(skill_positions):
            followers = set()
            for j in range(i + 1, min(i + 1 + CHAIN_WINDOW, len(events))):
                fsk = events[j]["skill"]
                if fsk and fsk != sk:
                    followers.add(fsk)
            chain_len_samples[sk].append(len(followers))
            # 바로 다음 스킬을 transition 으로 (윈도우 내 첫 다른 스킬)
            for j in range(i + 1, min(i + 1 + CHAIN_WINDOW, len(events))):
                fsk = events[j]["skill"]
                if fsk and fsk != sk:
                    transitions[(sk, fsk)] += 1
                    break

        # 마찰: 세션 사용자 발화에 마찰 표현이 있으면, 그 세션에 등장한 모든 스킬에 1 마찰
        session_has_friction = any(FRICTION_RE.search(t) for t in user_texts)
        for sk in session_skills:
            friction_sessions[sk][1] += 1
            if session_has_friction:
                friction_sessions[sk][0] += 1

        # slash command (raw 재스캔: 사용자 발화 안에 들어있음)
        for t in user_texts:
            for m in re.findall(r"<command-name>([^<]*)</command-name>", t):
                slash_cmds[m.strip().lstrip("/")] += 1

    # ── AutoScore 계산 ──
    auto_rows = []
    for sk, calls in skill_calls.items():
        samples = chain_len_samples.get(sk, [])
        avg_chain = sum(samples) / len(samples) if samples else 0.0
        fr = friction_sessions.get(sk, [0, 0])
        friction_rate = fr[0] / fr[1] if fr[1] else 0.0
        weekly = calls / span_weeks
        score = weekly * (avg_chain + 1) * (1 + friction_rate)  # 체인0이어도 빈도 반영되게 +1
        auto_rows.append((sk, score, weekly, avg_chain, friction_rate, calls))
    auto_rows.sort(key=lambda r: r[1], reverse=True)

    # ── 리포트 작성 ──
    out = []
    w = out.append
    w(f"# Skill Metrics — {since} ~ {until}  ({span_days}일)")
    w("")
    if args.project:
        w(f"- 프로젝트 필터: `{args.project}`")
    w(f"- 분석 세션: **{total_sessions}개**  (20줄 이하 빈 세션 제외)")
    reach = 100 * sessions_with_skill / total_sessions if total_sessions else 0
    areach = 100 * sessions_with_agent / total_sessions if total_sessions else 0
    w(f"- 스킬 도달률(Reach): **{reach:.0f}%** ({sessions_with_skill}/{total_sessions})"
      f" — 나머지 {100-reach:.0f}%는 스킬 미사용 세션(거시적 미활용 신호)")
    w(f"- 서브에이전트 도달률: **{areach:.0f}%** ({sessions_with_agent}/{total_sessions})")
    if total_skipped:
        w(f"- (파싱 건너뜀 라인: {total_skipped})")
    w("")

    # ① AutoScore
    w("## ① 자동화 우선순위 (AutoScore = 주간호출 × (평균체인+1) × (1+마찰율))")
    w("")
    w("| 스킬 | AutoScore | 주간호출 | 평균후속체인 | 마찰율 | 총호출 |")
    w("|---|---:|---:|---:|---:|---:|")
    for sk, score, weekly, avg_chain, frate, calls in auto_rows[: args.top]:
        w(f"| `{sk}` | {score:.1f} | {weekly:.1f} | {avg_chain:.2f} | {frate*100:.0f}% | {calls} |")
    w("")
    w("> 높을수록 자동화 임팩트 큼: 자주 + 다른 스킬과 엮여 + 마찰 동반.")
    w("")

    # 체인(transition) 묶음 후보
    w("## ①-b 묶음 후보 (A 직후 가장 자주 따라오는 B)")
    w("")
    w("| A → B | 횟수 |")
    w("|---|---:|")
    for (a, b), c in transitions.most_common(args.top):
        w(f"| `{a}` → `{b}` | {c} |")
    w("")
    w("> 같은 쌍이 반복되면 단일 체인 커맨드로 묶을 후보.")
    w("")

    # ③ 상시 지표
    w("## ③ 스킬 호출 빈도 (상위)")
    w("")
    w("| 스킬 | 호출 | 주간 |")
    w("|---|---:|---:|")
    for sk, c in skill_calls.most_common(args.top):
        w(f"| `{sk}` | {c} | {c/span_weeks:.1f} |")
    w("")

    w("## ③-b 일별 세션 분포")
    w("")
    w("| 날짜 | 세션 |")
    w("|---|---:|")
    for d in sorted(by_date):
        w(f"| {d} | {by_date[d]} |")
    w("")

    if slash_cmds:
        w("## (참고) 슬래시 커맨드 입력 빈도")
        w("")
        w("| 커맨드 | 입력 |")
        w("|---|---:|")
        for c, n in slash_cmds.most_common(args.top):
            w(f"| `/{c}` | {n} |")
        w("")

    report = "\n".join(out)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as fh:
            fh.write(report + "\n")
        print(f"saved: {args.out}  ({total_sessions} sessions)")
    else:
        print(report)


if __name__ == "__main__":
    main()
