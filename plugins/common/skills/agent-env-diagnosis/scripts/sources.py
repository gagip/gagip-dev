"""Claude Code·Codex 세션 기록을 찾아 같은 모양의 사건 목록으로 읽는다.

기록 위치는 각 도구의 표준 환경변수를 따른다.
  Claude Code: ${CLAUDE_CONFIG_DIR:-~/.claude}/projects/<project>/<session>.jsonl
  Codex:       ${CODEX_HOME:-~/.codex}/sessions/**/*.jsonl
               ${CODEX_HOME:-~/.codex}/archived_sessions/*.jsonl(.zst)

세션 파일은 프로세스 밖 자료라 깨진 줄·없는 필드는 건너뛰고 수를 센다.
.zst 는 zstd 명령이 있을 때만 읽고, 없으면 skipped_zst 로 센다.
"""

import glob
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field

SOURCES = ("claude", "codex")
SKIP_PREFIX = (
    "This session is being continued", "<local-command-caveat>", "<environment_context>",
    "# AGENTS.md", "<user_instructions>", "Caveat:", "[Request interrupted", "<task-notification>",
    "<side-sessions-event>", "<ci-monitor-event>", "Base directory for this skill", "<turn_aborted>",
)
SKILL_PATH_RE = re.compile(r"skills/([\w.-]+)/SKILL\.md")
SLASH_RE = re.compile(r"<command-name>(.*?)</command-name>(?:.*?<command-args>(.*?)</command-args>)?", re.S)


def claude_home():
    return os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude")


def codex_home():
    return os.path.expanduser(os.environ.get("CODEX_HOME") or "~/.codex")


@dataclass
class Event:
    """kind: user | text | tool | skill | agent.
    user: text=사용자 발화, tool: name=도구 이름·args=인자 문자열,
    skill: name=스킬 이름, agent: name=서브에이전트 종류, text: 에이전트 응답 글."""
    kind: str
    ts: str = ""
    name: str = ""
    text: str = ""
    args: str = ""


@dataclass
class Session:
    tool: str
    id: str
    path: str
    project: str = ""
    title: str = ""
    start: str = ""
    end: str = ""
    lines: int = 0
    bad_lines: int = 0
    compactions: int = 0
    interrupts: int = 0
    slash: list = field(default_factory=list)
    events: list = field(default_factory=list)
    fork_of: str = ""
    hooks: list = field(default_factory=list)  # (hookName, 첨부 종류) — Claude 만 기록한다

    def user_texts(self):
        return [e.text for e in self.events if e.kind == "user"]

    def skills(self):
        return [e.name for e in self.events if e.kind == "skill"]


@dataclass
class ScanStats:
    files: int = 0
    skipped_subagent: int = 0
    skipped_zst: int = 0
    unreadable: int = 0
    duplicates: int = 0
    fork_events_dropped: int = 0


def session_files(source="all"):
    """(tool, path) 목록. Claude 하위 세션(<session>/subagents/)은 깊이가 달라 잡히지 않는다."""
    if source not in ("all",) + SOURCES:
        raise ValueError(f"source 는 all|claude|codex 중 하나여야 한다: {source}")
    out = []
    if source in ("all", "claude"):
        out += [("claude", p) for p in glob.glob(os.path.join(claude_home(), "projects", "*", "*.jsonl"))]
    if source in ("all", "codex"):
        home = codex_home()
        out += [("codex", p) for p in glob.glob(os.path.join(home, "sessions", "**", "*.jsonl"), recursive=True)]
        out += [("codex", p) for p in glob.glob(os.path.join(home, "archived_sessions", "*.jsonl"))]
        out += [("codex", p) for p in glob.glob(os.path.join(home, "archived_sessions", "*.jsonl.zst"))]
    return sorted(out)


def read_lines(path):
    """(lines, error). error: None | 'zstd-missing' | 'unreadable'."""
    try:
        if path.endswith(".zst"):
            if not shutil.which("zstd"):
                return None, "zstd-missing"
            res = subprocess.run(["zstd", "-dc", path], capture_output=True)
            if res.returncode != 0:
                return None, "unreadable"
            return res.stdout.decode("utf-8", errors="replace").splitlines(), None
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines(), None
    except OSError:
        return None, "unreadable"


def strip_tags(text):
    return re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S).strip()


def _user_text(sess, ts, raw, is_meta=False):
    if raw.startswith("This session is being continued"):
        sess.compactions += 1
        return
    if raw.startswith("[Request interrupted") or raw.startswith("<turn_aborted>"):
        sess.interrupts += 1
        return
    for m in SLASH_RE.finditer(raw):
        sess.slash.append(m.group(1).strip().lstrip("/"))
    if is_meta or raw.startswith(SKIP_PREFIX):
        return
    m = SLASH_RE.search(raw)
    text = f"[/{m.group(1).strip().lstrip('/')}] {(m.group(2) or '').strip()}" if m else strip_tags(raw)
    if text:
        sess.events.append(Event("user", ts=ts, text=text))


def _stamp(sess, ts):
    if ts:
        sess.start = sess.start or ts
        sess.end = ts


def parse_claude(path, lines):
    sess = Session("claude", os.path.basename(path)[:-6], path, project=os.path.basename(os.path.dirname(path)), lines=len(lines))
    for line in lines:
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            sess.bad_lines += 1
            continue
        if not isinstance(d, dict):
            continue
        t, ts = d.get("type"), d.get("timestamp") or ""
        if t == "custom-title":
            sess.title = d.get("customTitle") or sess.title
        if d.get("cwd") and not sess.project.startswith("/"):
            sess.project = d["cwd"]
        att = d.get("attachment")
        if t == "attachment" and isinstance(att, dict) and att.get("hookName"):
            sess.hooks.append((att["hookName"], att.get("type", "?")))
        if t not in ("user", "assistant") or d.get("isSidechain"):
            continue
        _stamp(sess, ts)
        content = (d.get("message") or {}).get("content")
        if t == "user":
            texts = [content] if isinstance(content, str) else [
                c.get("text", "") for c in (content or []) if isinstance(c, dict) and c.get("type") == "text"]
            for raw in texts:
                if raw:
                    _user_text(sess, ts, raw, bool(d.get("isMeta")))
            continue
        for c in content or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "text" and c.get("text"):
                sess.events.append(Event("text", ts=ts, text=c["text"]))
            elif c.get("type") == "tool_use":
                name, inp = c.get("name", "?"), c.get("input") or {}
                sess.events.append(Event("tool", ts=ts, name=name, args=json.dumps(inp, ensure_ascii=False)))
                if name == "Skill":
                    sess.events.append(Event("skill", ts=ts, name=str(inp.get("skill", "?"))))
                elif name in ("Agent", "Task"):
                    sess.events.append(Event("agent", ts=ts, name=str(inp.get("subagent_type") or "general")))
    return sess


def parse_codex(path, lines):
    """하위 세션이면 None."""
    base = os.path.basename(path)
    sess = Session("codex", base.split(".jsonl")[0], path, lines=len(lines))
    for line in lines:
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            sess.bad_lines += 1
            continue
        if not isinstance(d, dict):
            continue
        p, ts = d.get("payload") or {}, d.get("timestamp") or ""
        if not isinstance(p, dict):
            continue
        if d.get("type") == "session_meta":
            src = p.get("source")
            if isinstance(src, dict) and "subagent" in src:
                return None
            sess.project = p.get("cwd") or ""
            continue
        ptype = p.get("type")
        if ptype in ("compaction", "compacted") or d.get("type") == "compacted":
            sess.compactions += 1
        if ptype == "turn_aborted":
            sess.interrupts += 1
        if d.get("type") != "response_item":
            continue
        _stamp(sess, ts)
        if ptype == "message":
            for c in p.get("content") or []:
                raw = c.get("text", "") if isinstance(c, dict) else ""
                if not raw:
                    continue
                if p.get("role") == "user":
                    _user_text(sess, ts, raw)
                elif p.get("role") == "assistant":
                    sess.events.append(Event("text", ts=ts, text=raw))
        elif ptype in ("function_call", "custom_tool_call", "local_shell_call"):
            args = p.get("arguments") or p.get("input") or p.get("action") or ""
            args = args if isinstance(args, str) else json.dumps(args, ensure_ascii=False)
            name = p.get("name") or ptype
            sess.events.append(Event("tool", ts=ts, name=name, args=args))
            for m in SKILL_PATH_RE.finditer(args):
                sess.events.append(Event("skill", ts=ts, name=m.group(1)))
            if name in ("spawn_agent", "create_agent"):
                sess.events.append(Event("agent", ts=ts, name="codex-agent"))
    return sess


def load_sessions(source="all", min_lines=20, since=None, until=None, project=None, stats=None):
    """기간(YYYY-MM-DD, 첫 기록 날짜 기준) 안의 사람 세션을 시작 시각 순으로 돌려준다."""
    stats = stats if stats is not None else ScanStats()
    out, seen = [], set()
    for tool, path in session_files(source):
        stats.files += 1
        lines, err = read_lines(path)
        if err == "zstd-missing":
            stats.skipped_zst += 1
            continue
        if err:
            stats.unreadable += 1
            continue
        if len(lines) <= min_lines:
            continue
        sess = parse_claude(path, lines) if tool == "claude" else parse_codex(path, lines)
        if sess is None:
            stats.skipped_subagent += 1
            continue
        if (sess.tool, sess.id) in seen:
            stats.duplicates += 1
            continue
        seen.add((sess.tool, sess.id))
        day = sess.start[:10]
        if not day or (since and day < since) or (until and day > until):
            continue
        if project and project not in (sess.project or "") and project not in path:
            continue
        out.append(sess)
    out.sort(key=lambda s: (s.start, s.path))
    trim_forks(out, stats)
    return out


def _sig(e):
    return (e.kind, e.ts, e.name, e.text[:80], e.args[:80])


def trim_forks(sessions, stats=None):
    """기존 세션을 복제해 이어 간 세션(첫 사용자 발화의 시각·내용이 앞선 세션과 같음)에 fork_of 를 적고,
    원래 세션에서 복사해 온 사건을 지운다. 그래야 스킬 호출·파일 열람·교정을 두 번 세지 않는다."""
    owner = {}
    for s in sessions:
        first = next((e for e in s.events if e.kind == "user"), None)
        if first is None:
            continue
        k = (first.ts, first.text[:120])
        if k not in owner:
            owner[k] = s
            continue
        src = owner[k]
        s.fork_of = f"{src.tool}:{src.id}"
        copied = {_sig(e) for e in src.events}
        before = len(s.events)
        s.events = [e for e in s.events if _sig(e) not in copied]
        if stats is not None:
            stats.fork_events_dropped += before - len(s.events)
