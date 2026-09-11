#!/usr/bin/env python3
"""
agent_trace — 세션 로그에서 서브에이전트 실행 이력을 뽑아 마크다운으로 낸다.

회고가 "에이전트가 무엇을 받아 무엇을 냈고 사용자가 어떻게 반응했나"를 판정할 수 있도록
원재료만 모아 준다. 좋았는지 나빴는지는 판정하지 않는다 — 그건 읽는 쪽의 일이다.

추출 항목: 위임 프롬프트 / 보고서 / 직후 사용자 발화 / 토큰·시간·도구 / 동시 실행 여부.

주의(계약): 세션 파일은 프로세스 경계(외부 파일)다. 깨진 라인·누락 필드는 예외로 죽이지 않고
건너뛴 뒤 끝에 건너뛴 수를 보고한다. 값을 못 구한 칸은 0이 아니라 "계산 불가"로 적는다.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta

PROJECTS_DIR = os.path.expanduser("~/.claude/projects")
MIN_LINES = 20          # 이보다 짧은 세션은 즉시 종료된 빈 세션 → 제외 (skill-metrics 와 같은 기준)
HEAD_CHARS = 800        # --full 이 없을 때 보고서 앞부분
TAIL_CHARS = 400        # --full 이 없을 때 보고서 뒷부분

NOTIF_RE = re.compile(r"<task-notification>(.*?)</task-notification>", re.S)
REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
# 사람이 친 것처럼 기록되지만 실제로는 하네스가 넣은 문구 — 반응으로 읽으면 안 된다.
SYNTHETIC_RE = re.compile(r"^\[(Request interrupted|No response requested)")


def parse_args():
    p = argparse.ArgumentParser(description="세션 로그의 서브에이전트 실행 이력 추출")
    p.add_argument("--session", help="세션 JSONL 경로 하나")
    p.add_argument("--project", help="세션 경로에 이 문자열이 든 것만")
    p.add_argument("--days", type=int, help="최근 N일 (기간 회고용)")
    p.add_argument("--full", action="store_true", help="보고서 전문 출력 (기본은 앞뒤만)")
    p.add_argument("--out", help="마크다운 저장 경로 (미지정 시 stdout)")
    return p.parse_args()


# ── 세션 고르기 ────────────────────────────────────────────────────────────────

def cwd_slug(path):
    """작업 디렉터리 경로 → 로그 폴더 이름. 예: /Users/me/a.b → -Users-me-a-b"""
    return path.replace("/", "-").replace(".", "-")


def line_count(path):
    try:
        with open(path, errors="ignore") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def first_date(path):
    try:
        with open(path, errors="ignore") as fh:
            for line in fh:
                m = re.search(r'"timestamp":"(\d{4}-\d{2}-\d{2})', line)
                if m:
                    return m.group(1)
    except OSError:
        return None
    return None


def collect_sessions(args):
    """분석할 세션 파일 목록. 아무 조건도 없으면 현재 작업 디렉터리의 최신 세션 하나."""
    if args.session:
        return [args.session]
    if not os.path.isdir(PROJECTS_DIR):
        return []

    roots = []
    if not args.project and not args.days:
        here = os.path.join(PROJECTS_DIR, cwd_slug(os.getcwd()))
        if os.path.isdir(here):
            roots = [here]
    if not roots:
        roots = [PROJECTS_DIR]

    found = []
    for root in roots:
        for dirpath, _dirs, files in os.walk(root):
            # 서브에이전트 기록은 부모 세션을 통해 따로 연다 — 세션 목록에는 넣지 않는다.
            if "subagents" in dirpath.split(os.sep):
                continue
            for fn in files:
                if not fn.endswith(".jsonl"):
                    continue
                path = os.path.join(dirpath, fn)
                if args.project and args.project not in path:
                    continue
                if line_count(path) <= MIN_LINES:
                    continue
                found.append(path)

    if args.days:
        since = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        found = [p for p in found if (first_date(p) or "") >= since]
        found.sort(key=lambda p: first_date(p) or "")
        return found

    if not found:
        return []
    if args.project:
        found.sort(key=lambda p: first_date(p) or "")
        return found
    # 조건이 없으면 최신 하나
    return [max(found, key=os.path.getmtime)]


# ── 로그 읽기 ──────────────────────────────────────────────────────────────────

def read_entries(path):
    entries, skipped = [], 0
    try:
        fh = open(path, errors="ignore")
    except OSError:
        return entries, 1
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                skipped += 1
    return entries, skipped


def block_text(content):
    """message.content 를 평문으로. 문자열/블록리스트 양쪽을 받는다."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def is_human(entry):
    """사람이 친 발화인가. 시스템 알림·도구 결과·서브에이전트 내부 발화는 아니다."""
    if entry.get("type") != "user" or entry.get("isSidechain"):
        return False
    origin = entry.get("origin")
    if isinstance(origin, dict):
        return origin.get("kind") == "human"
    # origin 을 안 남기는 버전 — 도구 결과·완료 알림을 걸러내고 판단한다.
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return False
    text = block_text(content)
    return bool(text.strip()) and "<task-notification>" not in text


def clean(text):
    return REMINDER_RE.sub("", text or "").strip()


def parse_notifications(entries):
    """완료 알림을 tool-use-id 로 색인. 같은 에이전트가 여러 번 알릴 수 있어 마지막 것을 쓴다."""
    by_tool_use = {}
    for e in entries:
        if e.get("type") != "user":
            continue
        text = block_text((e.get("message") or {}).get("content"))
        for body in NOTIF_RE.findall(text):
            def tag(name):
                m = re.search(rf"<{name}>(.*?)</{name}>", body, re.S)
                return m.group(1).strip() if m else None
            tuid = tag("tool-use-id")
            if not tuid:
                continue
            by_tool_use[tuid] = {
                "status": tag("status"),
                "result": tag("result"),
                "ts": e.get("timestamp"),
            }
    return by_tool_use


def parse_results(entries):
    """동기 실행 결과를 tool_use_id 로 색인."""
    by_tool_use = {}
    for e in entries:
        tur = e.get("toolUseResult")
        if not isinstance(tur, dict) or not tur.get("agentId"):
            continue
        content = (e.get("message") or {}).get("content")
        tuid = None
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    tuid = b.get("tool_use_id")
        if not tuid:
            continue
        by_tool_use[tuid] = {
            "agent_id": tur.get("agentId"),
            "status": tur.get("status"),
            # 비동기는 즉시 반환되므로 이 항목의 timestamp 는 완료가 아니라 접수 시각이다.
            "is_async": tur.get("status") == "async_launched" or bool(tur.get("isAsync")),
            "model": tur.get("resolvedModel"),
            "duration_ms": tur.get("totalDurationMs"),
            "total_tokens": tur.get("totalTokens"),
            "tool_count": tur.get("totalToolUseCount"),
            "tool_stats": tur.get("toolStats") or {},
            "report": block_text(tur.get("content")),
            "ts": e.get("timestamp"),
        }
    return by_tool_use


# ── 서브에이전트 트랜스크립트 ─────────────────────────────────────────────────

def transcript_path(session_path, agent_id):
    base = session_path[:-len(".jsonl")] if session_path.endswith(".jsonl") else session_path
    return os.path.join(base, "subagents", f"agent-{agent_id}.jsonl")


def transcript_metrics(path):
    """비동기 실행처럼 부모 로그에 지표가 없을 때 트랜스크립트에서 직접 센다.
    파일이 없으면 None — 호출부가 '계산 불가'로 적는다."""
    if not os.path.isfile(path):
        return None
    stamps, out_tokens, tools, model = [], 0, 0, None
    counts = {"readCount": 0, "searchCount": 0, "bashCount": 0, "editFileCount": 0, "otherToolCount": 0}
    entries, _ = read_entries(path)
    for e in entries:
        if e.get("timestamp"):
            stamps.append(e["timestamp"])
        msg = e.get("message") or {}
        if e.get("type") != "assistant":
            continue
        model = msg.get("model") or model
        out_tokens += (msg.get("usage") or {}).get("output_tokens", 0)
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            tools += 1
            name = b.get("name", "")
            if name == "Read":
                counts["readCount"] += 1
            elif name in ("Grep", "Glob"):
                counts["searchCount"] += 1
            elif name == "Bash":
                counts["bashCount"] += 1
            elif name in ("Edit", "Write", "NotebookEdit"):
                counts["editFileCount"] += 1
            else:
                counts["otherToolCount"] += 1
    if not stamps:
        return None
    span = to_dt(max(stamps)) - to_dt(min(stamps))
    return {
        "duration_ms": int(span.total_seconds() * 1000),
        "output_tokens": out_tokens,
        "tool_count": tools,
        "tool_stats": counts,
        "model": model,
    }


def to_dt(stamp):
    return datetime.strptime(stamp[:19], "%Y-%m-%dT%H:%M:%S")


# ── 조립 ──────────────────────────────────────────────────────────────────────

def build_records(session_path, entries):
    results = parse_results(entries)
    notifs = parse_notifications(entries)

    records = []
    turn = 0
    human_stamps = []
    for e in entries:
        if is_human(e):
            turn += 1
            human_stamps.append((e.get("timestamp"), clean(block_text((e.get("message") or {}).get("content")))))
        if e.get("type") != "assistant" or e.get("isSidechain"):
            continue
        content = (e.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict) or b.get("type") != "tool_use" or b.get("name") != "Agent":
                continue
            inp = b.get("input") or {}
            tuid = b.get("id")
            res = results.get(tuid, {})
            notif = notifs.get(tuid, {})
            rec = {
                "turn": turn,
                "tool_use_id": tuid,
                "agent_type": inp.get("subagent_type") or "(미지정)",
                "description": inp.get("description") or "",
                "prompt": inp.get("prompt") or "",
                "is_async": res.get("is_async", bool(inp.get("run_in_background"))),
                "start": e.get("timestamp"),
                "agent_id": res.get("agent_id"),
                "model": res.get("model"),
                "status": res.get("status"),
                "report": res.get("report") or "",
                # 동기 실행일 때만 결과 timestamp 가 곧 완료 시각이다.
                "end": None if res.get("is_async") else res.get("ts"),
                "duration_ms": res.get("duration_ms"),
                "total_tokens": res.get("total_tokens"),
                "tool_count": res.get("tool_count"),
                "tool_stats": res.get("tool_stats") or {},
                "metrics_source": "하네스 보고",
            }
            # 비동기로 띄운 경우 — 부모 로그에 지표가 없다. 완료 알림과 트랜스크립트로 채운다.
            if rec["status"] != "completed":
                if notif:
                    rec["status"] = notif.get("status") or rec["status"]
                    rec["report"] = notif.get("result") or rec["report"]
                    rec["end"] = notif.get("ts") or rec["end"]
                tm = transcript_metrics(transcript_path(session_path, rec["agent_id"])) if rec["agent_id"] else None
                if tm:
                    rec.update({
                        "duration_ms": tm["duration_ms"],
                        "tool_count": tm["tool_count"],
                        "tool_stats": tm["tool_stats"],
                        "output_tokens": tm["output_tokens"],
                        "model": rec["model"] or tm["model"],
                        "metrics_source": "트랜스크립트 계산",
                    })
                else:
                    rec["metrics_source"] = None      # 계산 불가 — 0 으로 적지 않는다
            records.append(rec)

    # 완료 시각을 못 구했으면 시작 + 소요로 메운다. 둘 다 없으면 비워 둔다.
    for rec in records:
        if not rec["end"] and rec["start"] and rec["duration_ms"]:
            finished = to_dt(rec["start"]) + timedelta(milliseconds=rec["duration_ms"])
            rec["end"] = finished.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

    # 직후 사용자 발화 — 에이전트가 끝난 뒤 처음 나온 사람 발화.
    # 완료 시각을 모르면 짝짓지 않는다. 접수 시각으로 짝지으면 실행 중에 한 말이 "반응"으로 둔갑한다.
    for rec in records:
        end = rec["end"]
        rec["reaction"] = None
        if not end:
            continue
        for stamp, text in human_stamps:
            if stamp and stamp > end and text and not SYNTHETIC_RE.match(text):
                rec["reaction"] = (stamp, text)
                break

    mark_concurrent(records)
    return records


def mark_concurrent(records):
    """실행 구간이 겹치는 에이전트를 같은 묶음으로 표시한다.
    한 요청에서 여러 개를 띄웠어도 앞이 끝난 뒤 다음을 띄웠으면 병렬이 아니다."""
    for rec in records:
        rec["concurrent_with"] = 0
    for i, a in enumerate(records):
        if not (a["start"] and a["end"]):
            continue
        for j, b in enumerate(records):
            if i == j or not (b["start"] and b["end"]):
                continue
            if a["start"] < b["end"] and b["start"] < a["end"]:
                a["concurrent_with"] += 1


# ── 출력 ──────────────────────────────────────────────────────────────────────

def quote(text, limit=None):
    text = clean(text)
    if not text:
        return "> (없음)"
    if limit and len(text) > limit[0] + limit[1]:
        text = text[: limit[0]] + "\n\n… (중략) …\n\n" + text[-limit[1]:]
    return "\n".join("> " + line for line in text.splitlines())


def fmt_duration(ms):
    if ms is None:
        return "시간 계산 불가"
    sec = ms / 1000
    return f"{sec:.0f}초" if sec < 60 else f"{int(sec // 60)}분 {sec % 60:.0f}초"


def render(session_path, records, skipped, full):
    out = []
    w = out.append
    name = os.path.basename(session_path)[:8]
    date = first_date(session_path) or "?"
    w(f"## 에이전트 실행 이력 — {name} ({date})")
    w("")
    if not records:
        w("에이전트 실행 없음.")
        w("")
        return out

    total_ms = sum(r["duration_ms"] or 0 for r in records)
    unfinished = [r for r in records if (r["status"] or "") not in ("completed",)]
    unmeasured = [r for r in records if r["metrics_source"] is None]
    # 합산이다 — 병렬로 돌았으면 실제 걸린 시간은 이보다 짧다.
    w(f"에이전트 **{len(records)}건** · 소요 합산 {fmt_duration(total_ms)}"
      + (f" · 정상 종료 아님 {len(unfinished)}건" if unfinished else ""))
    if unmeasured:
        w(f"- 지표 계산 불가 {len(unmeasured)}건 (서브에이전트 기록이 남지 않은 실행)")
    if skipped:
        w(f"- 파싱 건너뛴 라인 {skipped}줄")
    w("- Codex 세션 미포함 — 이 스크립트는 Claude 로그만 읽는다.")
    w("")

    for i, r in enumerate(records, 1):
        w(f"### {i}. {r['agent_type']} — \"{r['description']}\"")
        bits = [r["model"] or "모델 미상"]
        bits.append("비동기" if r["is_async"] else "동기")
        bits.append(fmt_duration(r["duration_ms"]))
        if r.get("total_tokens"):
            bits.append(f"{r['total_tokens']:,}토큰(하네스 보고)")
        elif r.get("output_tokens"):
            bits.append(f"출력 {r['output_tokens']:,}토큰")
        if r["tool_count"] is not None:
            stats = r["tool_stats"]
            detail = " · ".join(
                f"{label} {stats.get(key, 0)}"
                for key, label in (("readCount", "읽기"), ("searchCount", "검색"),
                                   ("bashCount", "bash"), ("editFileCount", "편집"))
                if stats.get(key)
            )
            bits.append(f"도구 {r['tool_count']}회" + (f"({detail})" if detail else ""))
        w("- " + " · ".join(bits))
        if r["metrics_source"] is None:
            w("- ⚠ 지표 계산 불가 — 서브에이전트 기록 없음 (0이 아니라 미측정)")
        if r["status"] == "async_launched":
            w("- ⚠ 완료 알림 없음 — 이 세션 안에서 끝나지 않았거나 알림이 유실됐다")
        elif (r["status"] or "") != "completed":
            w(f"- ⚠ 종료 상태: {r['status'] or '결과 기록 없음'}")
        if r["concurrent_with"]:
            w(f"- 동시 실행: 다른 에이전트 {r['concurrent_with']}개와 구간이 겹침")
        else:
            w("- 동시 실행: 없음 (단독)")
        w("")
        w(f"**위임 프롬프트** ({len(r['prompt']):,}자)")
        w("")
        w(quote(r["prompt"]))
        w("")
        report = r["report"]
        trimmed = "" if full or len(report) <= HEAD_CHARS + TAIL_CHARS else ", 잘림"
        w(f"**보고서** ({len(report):,}자{trimmed})")
        w("")
        w(quote(report, None if full else (HEAD_CHARS, TAIL_CHARS)))
        w("")
        if r["reaction"]:
            stamp, text = r["reaction"]
            w(f"**직후 사용자 발화** ({stamp[11:19]})")
            w("")
            w(quote(text, (600, 200)))
        elif not r["end"]:
            w("**직후 사용자 발화** — 완료 시각을 몰라 짝지을 수 없음")
        else:
            w("**직후 사용자 발화** — 없음 (세션이 끝났거나 사용자가 반응하지 않음)")
        w("")
    return out


def main():
    args = parse_args()
    sessions = collect_sessions(args)
    if not sessions:
        print("분석할 세션을 찾지 못했다. --session 으로 경로를 직접 주거나 --project 로 범위를 넓혀라.",
              file=sys.stderr)
        return 1

    out = []
    for path in sessions:
        entries, skipped = read_entries(path)
        records = build_records(path, entries)
        if len(sessions) > 1 and not records:
            continue          # 기간 회고에서 빈 세션까지 나열하지 않는다
        out.extend(render(path, records, skipped, args.full))

    if not out:
        out = ["에이전트를 띄운 세션이 없다."]
    report = "\n".join(out)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as fh:
            fh.write(report + "\n")
        print(f"saved: {args.out}  ({len(sessions)} sessions)")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
