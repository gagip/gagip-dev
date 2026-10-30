"""가짜 Claude·Codex 세션 파일로 기록 읽기·추출·대조·집계를 확인한다.

실행: python3 -m unittest discover -s plugins/common/skills/agent-env-diagnosis/scripts -p 'test_*.py'
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aggregate  # noqa: E402
import check_chunks  # noqa: E402
import env_scan  # noqa: E402
import extract  # noqa: E402
import measure  # noqa: E402
import sources  # noqa: E402

PAD = 22


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False)


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def first_line(path):
    with open(path, encoding="utf-8") as fh:
        return json.loads(fh.readline())


def claude_rows(first_prompt, correction, skills=(), opened=(), ts="2026-10-01T01:00:00Z"):
    rows = [{"type": "user", "timestamp": ts, "cwd": "/work/app", "message": {"content": first_prompt}}]
    for sk in skills:
        rows.append({"type": "assistant", "timestamp": "2026-10-01T01:01:00Z", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": sk}}]}})
    for p in opened:
        rows.append({"type": "assistant", "timestamp": "2026-10-01T01:02:00Z", "message": {"content": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": p}}]}})
    rows.append({"type": "assistant", "timestamp": "2026-10-01T01:03:00Z", "message": {"content": [
        {"type": "text", "text": "보고서를 마크다운으로 정리했습니다."}]}})
    rows.append({"type": "user", "timestamp": "2026-10-01T01:04:00Z", "message": {"content": correction}})
    rows += [{"type": "assistant", "timestamp": "2026-10-01T01:05:00Z", "message": {"content": [{"type": "text", "text": "."}]}}] * PAD
    return rows


def codex_rows(source="cli", skill_in_args=True):
    rows = [{"type": "session_meta", "timestamp": "2026-10-02T01:00:00Z", "payload": {"id": "cx-1", "cwd": "/work/app", "source": source}},
            {"type": "response_item", "timestamp": "2026-10-02T01:00:01Z", "payload": {"type": "message", "role": "developer", "content": [
                {"type": "input_text", "text": "사용할 수 있는 스킬: /x/skills/listed-only/SKILL.md"}]}},
            {"type": "response_item", "timestamp": "2026-10-02T01:00:02Z", "payload": {"type": "message", "role": "user", "content": [
                {"type": "input_text", "text": "계획서 써줘"}]}}]
    if skill_in_args:
        rows.append({"type": "response_item", "timestamp": "2026-10-02T01:00:03Z", "payload": {
            "type": "function_call", "name": "exec_command", "arguments": json.dumps({"cmd": "sed -n 1,80p /p/skills/work-plan/SKILL.md"})}})
    rows += [{"type": "response_item", "timestamp": "2026-10-02T01:00:04Z", "payload": {"type": "message", "role": "assistant", "content": [
        {"type": "output_text", "text": "."}]}}] * PAD
    return rows


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.claude = os.path.join(self.tmp, "claude")
        self.codex = os.path.join(self.tmp, "codex")
        self.env = mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": self.claude, "CODEX_HOME": self.codex})
        self.env.start()
        proj = os.path.join(self.claude, "projects", "-work-app")
        self.mem = os.path.join(self.tmp, "memory")
        os.makedirs(self.mem)
        for name in ("feedback-a.md", "feedback-b.md", "MEMORY.md"):
            write_json(os.path.join(self.mem, name), "- 규칙")
        source_rows = claude_rows("보고서 만들어줘", "아니 HTML로 달라고 했잖아", skills=("work-plan", "html-brief"),
                                  opened=(os.path.join(self.mem, "feedback-a.md"),))
        write_jsonl(os.path.join(proj, "s-a.jsonl"), source_rows)
        write_jsonl(os.path.join(proj, "s-fork.jsonl"), source_rows + [
            {"type": "user", "timestamp": "2026-10-01T02:00:00Z", "message": {"content": "이어서 표도 넣어줘"}}])
        write_jsonl(os.path.join(proj, "s-other.jsonl"),
                    claude_rows("다른 보고서 만들어줘", "아니 HTML로 달라고 했잖아", ts="2026-10-05T01:00:00Z"))
        write_jsonl(os.path.join(proj, "s-short.jsonl"), claude_rows("짧다", "끝")[:5])
        write_jsonl(os.path.join(proj, "s-a", "subagents", "agent-1.jsonl"), claude_rows("하위", "하위", skills=("x",)))
        write_jsonl(os.path.join(self.codex, "sessions", "2026", "10", "02", "rollout-1.jsonl"), codex_rows())
        write_jsonl(os.path.join(self.codex, "sessions", "2026", "10", "02", "rollout-sub.jsonl"),
                    codex_rows(source={"subagent": {"thread_spawn": {}}}))
        self.out = os.path.join(self.tmp, "out")

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp)

    def quiet(self, fn, *a):
        with redirect_stdout(io.StringIO()):
            return fn(*a)


class SourcesTest(Fixture):
    def test_claude_reads_main_sessions_only(self):
        ss = sources.load_sessions("claude")
        self.assertEqual(sorted(s.id for s in ss), ["s-a", "s-fork", "s-other"])
        self.assertEqual(next(s for s in ss if s.id == "s-a").skills(), ["work-plan", "html-brief"])

    def test_codex_counts_skill_only_from_tool_args_and_skips_subagent(self):
        st = sources.ScanStats()
        ss = sources.load_sessions("codex", stats=st)
        self.assertEqual(len(ss), 1)
        self.assertEqual(ss[0].skills(), ["work-plan"])
        self.assertEqual(st.skipped_subagent, 1)

    def test_same_id_twice_resumed_codex_kept_copied_claude_dropped(self):
        write_jsonl(os.path.join(self.codex, "sessions", "2026", "10", "03", "rollout-2.jsonl"), codex_rows())
        write_jsonl(os.path.join(self.claude, "projects", "-moved-app", "s-a.jsonl"),
                    claude_rows("보고서 만들어줘", "아니 HTML로 달라고 했잖아"))
        st = sources.ScanStats()
        ss = sources.load_sessions("all", stats=st)
        keys = [f"{s.tool}:{s.id}" for s in ss]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(sum(1 for s in ss if s.tool == "codex"), 2)
        self.assertEqual(st.duplicates, 1)

    def test_codex_zst_read_or_counted_when_zstd_missing(self):
        plain = os.path.join(self.codex, "sessions", "2026", "10", "02", "rollout-1.jsonl")
        if not shutil.which("zstd"):
            self.skipTest("zstd 없음")
        os.makedirs(os.path.join(self.codex, "archived_sessions"))
        subprocess.run(["zstd", "-q", plain, "-o", os.path.join(self.codex, "archived_sessions", "old.jsonl.zst")], check=True)
        self.assertEqual(len(sources.load_sessions("codex")), 2)
        with mock.patch.object(sources.shutil, "which", return_value=None):
            st = sources.ScanStats()
            self.assertEqual(len(sources.load_sessions("codex", stats=st)), 1)
            self.assertEqual(st.skipped_zst, 1)


class MeasureTest(Fixture):
    def test_skill_calls_and_transition(self):
        m = measure.measure(sources.load_sessions("all"), 1.0)
        self.assertEqual(m["skill_calls"]["html-brief"], 1)
        self.assertEqual(m["transitions"][("work-plan", "html-brief")], 1)
        self.assertEqual(m["skill_sessions"], 2)


class EnvScanTest(Fixture):
    def test_memory_opened_and_never_opened(self):
        r = env_scan.scan(sources.load_sessions("all"), [], [], self.mem, [])
        opened = {os.path.basename(m["file"]): m["opened_sessions"] for m in r["memory"]}
        self.assertEqual(opened, {"MEMORY.md": 0, "feedback-a.md": 1, "feedback-b.md": 0})


class PipelineTest(Fixture):
    def run_sessions(self):
        self.quiet(extract.main, ["sessions", "--out-dir", self.out, "--since", "2026-09-01", "--until", "2026-10-31", "--exclude"])
        with open(os.path.join(self.out, "sessions.jsonl"), encoding="utf-8") as fh:
            return {r["key"]: r for r in map(json.loads, fh)}

    def classify(self, recs):
        os.makedirs(os.path.join(self.out, "classified"))
        rows = [dict(id=k, work_type="기획", stages=["요청", "문서작성"],
                     corrections=[dict(quote="아니 HTML로 달라고 했잖아", stage="문서작성")] if r["tool"] == "claude" else [])
                for k, r in recs.items()]
        write_json(os.path.join(self.out, "classified", "chunk_01.json"), rows)

    def test_fork_marked_and_copied_quote_counted_once(self):
        recs = self.run_sessions()
        self.assertEqual(recs["claude:s-fork"]["fork_of"], "claude:s-a")
        self.assertEqual(recs["claude:s-fork"]["user_msgs"], 1)
        self.classify(recs)
        self.quiet(extract.main, ["context", "--out-dir", self.out])
        meta = read_json(os.path.join(self.out, "context_meta.json"))
        self.assertEqual((meta["candidates"], meta["duplicates_removed"]), (2, 1))
        ctx = next(r for r in map(json.loads, open(os.path.join(self.out, "context", "ctx_01.jsonl"), encoding="utf-8"))
                   if r["session"] == "claude:s-a")
        self.assertIn("마크다운", ctx["agent_reply_before"])
        self.assertTrue(any(p.endswith("memory/feedback-a.md") for p in ctx["md_opened_before"]))

    def test_check_chunks_flags_missing_session(self):
        recs = self.run_sessions()
        os.makedirs(os.path.join(self.out, "classified"))
        write_json(os.path.join(self.out, "classified", "chunk_01.json"), [dict(id=next(iter(recs)))])
        self.assertTrue(self.quiet(check_chunks.check, self.out, "classified"))

    def test_aggregate_cause_and_rule_loaded(self):
        recs = self.run_sessions()
        self.classify(recs)
        self.quiet(extract.main, ["context", "--out-dir", self.out])
        os.makedirs(os.path.join(self.out, "judged"))
        n = next(r["n"] for r in map(json.loads, open(os.path.join(self.out, "context", "ctx_01.jsonl"), encoding="utf-8"))
                 if r["session"] == "claude:s-a")
        write_json(os.path.join(self.out, "judged", "judged_01.json"),
                   [dict(n=n, real=True, kind="산출물형식", stage="문서작성", cause="규칙있음_어김", rule_place="메모리",
                         rule_file=os.path.join(self.mem, "feedback-a.md"), rule_text="보고는 HTML", what="형식 틀림")])
        data, base, corr = aggregate.build(self.out)
        self.assertEqual(dict(data["causes"])["규칙있음_어김"], 1)
        self.assertIs(corr[0]["loaded"], True)
        self.assertEqual(data["place_loaded"][2], ["메모리", 1, 0, 0])
        self.assertIn("기획|문서작성|산출물형식", base["cells"])


    def test_check_chunks_fails_when_nothing_to_compare(self):
        os.makedirs(self.out)
        self.assertTrue(self.quiet(check_chunks.check, self.out, "classified"))

    def test_no_candidates_writes_no_context_parts(self):
        recs = self.run_sessions()
        os.makedirs(os.path.join(self.out, "classified"))
        write_json(os.path.join(self.out, "classified", "chunk_01.json"), [dict(id=k, corrections=[]) for k in recs])
        self.quiet(extract.main, ["context", "--out-dir", self.out])
        self.assertEqual([f for f in os.listdir(os.path.join(self.out, "context")) if f.startswith("ctx_")], [])


class RuleLoadedTest(unittest.TestCase):
    def test_relative_open_and_skill_reference_count_as_loaded(self):
        mem = dict(rule_place="메모리", rule_file="/h/.claude/projects/p/memory/feedback-x.md")
        self.assertIs(aggregate.rule_loaded(mem, {}, ["memory/feedback-x.md"]), True)
        self.assertIs(aggregate.rule_loaded(mem, {}, ["/other/proj/memory/feedback-x.md"]), False)
        skill = dict(rule_place="스킬", rule_file="/p/plugins/common/skills/grill/references/a.md")
        self.assertIs(aggregate.rule_loaded(skill, {"skills_so_far": ["common:grill"]}, []), True)


if __name__ == "__main__":
    unittest.main()
