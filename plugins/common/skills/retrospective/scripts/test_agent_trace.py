"""비동기 에이전트의 완료 알림·보고서가 로그 어느 자리에 남아도 읽히는지, 현재 세션을 환경변수로 고르는지 확인한다.

실행: python3 test_agent_trace.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import agent_trace  # noqa: E402

AGENT_ID = "a1b2c3"
TOOL_USE_ID = "toolu_x1"
REPORT = "## 결과\n- 확인됨 3건\n- 틀림 0건"
PLACEHOLDER = f'This agent\'s report was delivered to you as a message from "{AGENT_ID}" (its SubagentHandback call).'


def notification(status="completed", result=PLACEHOLDER):
    return (f"<task-notification>\n<task-id>{AGENT_ID}</task-id>\n<tool-use-id>{TOOL_USE_ID}</tool-use-id>\n"
            f"<status>{status}</status>\n<result>{result}</result>\n</task-notification>")


def handback_inner():
    indented = "\n".join("  " + line for line in REPORT.split("\n"))
    return f"[Subagent hand-back] The text below is the final report. The report follows:\n{indented}"


def handback():
    return f'<agent-message from="{AGENT_ID}">\n{handback_inner()}\n</agent-message>'


def launch_entries():
    return [
        {"type": "assistant", "timestamp": "2026-01-01T00:00:00.000Z",
         "message": {"content": [{"type": "tool_use", "name": "Agent", "id": TOOL_USE_ID,
                                  "input": {"description": "검토", "prompt": "읽기 전용 검토",
                                            "subagent_type": "general-purpose"}}]}},
        {"type": "user", "timestamp": "2026-01-01T00:00:01.000Z",
         "toolUseResult": {"agentId": AGENT_ID, "status": "async_launched", "isAsync": True},
         "message": {"content": [{"type": "tool_result", "tool_use_id": TOOL_USE_ID, "content": "launched"}]}},
    ]


def record_for(extra_entries):
    records = agent_trace.build_records("/nonexistent/session.jsonl", launch_entries() + extra_entries)
    assert len(records) == 1
    return records[0]


class DeliveredSomewhere(unittest.TestCase):
    def test_queue_enqueue(self):
        rec = record_for([
            {"type": "queue-operation", "operation": "enqueue", "timestamp": "2026-01-01T00:05:00.000Z",
             "content": handback()},
            {"type": "queue-operation", "operation": "enqueue", "timestamp": "2026-01-01T00:05:01.000Z",
             "content": notification()},
            {"type": "queue-operation", "operation": "remove", "timestamp": "2026-01-01T00:05:30.000Z",
             "content": notification()},
        ])
        self.assertEqual(rec["status"], "completed")
        self.assertEqual(rec["report"], REPORT)
        self.assertEqual(rec["end"], "2026-01-01T00:05:01.000Z")

    def test_attachment_queued_command(self):
        rec = record_for([
            {"type": "attachment", "timestamp": "2026-01-01T00:05:01.000Z",
             "attachment": {"type": "queued_command", "prompt": notification()}},
            {"type": "attachment", "timestamp": "2026-01-01T00:05:02.000Z",
             "attachment": {"type": "queued_command", "prompt": handback()}},
        ])
        self.assertEqual(rec["status"], "completed")
        self.assertEqual(rec["report"], REPORT)

    def test_peer_user_entry_is_report_not_human_reaction(self):
        rec = record_for([
            {"type": "user", "timestamp": "2026-01-01T00:05:00.000Z",
             "origin": {"kind": "peer", "from": AGENT_ID, "body": handback_inner()},
             "message": {"content": "Another session sent a message:\n" + handback()}},
            {"type": "user", "timestamp": "2026-01-01T00:05:01.000Z",
             "message": {"content": notification()}},
        ])
        self.assertEqual(rec["report"], REPORT)
        self.assertIsNone(rec["reaction"])

    def test_report_in_notification_result_still_used(self):
        rec = record_for([
            {"type": "user", "timestamp": "2026-01-01T00:05:01.000Z",
             "message": {"content": notification(result="보고서 본문")}},
        ])
        self.assertEqual(rec["report"], "보고서 본문")


class CurrentSession(unittest.TestCase):
    def test_env_session_id_picks_log_regardless_of_cwd(self):
        with tempfile.TemporaryDirectory() as root:
            project = Path(root, "-some-project")
            project.mkdir()
            target = project / "sess-123.jsonl"
            target.write_text("{}\n")
            newer = project / "other.jsonl"
            newer.write_text("{}\n" * 50)
            args = mock.Mock(session=None, project=None, days=None)
            with mock.patch.object(agent_trace, "PROJECTS_DIR", root), \
                    mock.patch.dict(os.environ, {agent_trace.SESSION_ID_ENV: "sess-123"}):
                self.assertEqual(agent_trace.collect_sessions(args), [str(target)])

    def test_missing_env_falls_back(self):
        with tempfile.TemporaryDirectory() as root:
            args = mock.Mock(session=None, project=None, days=None)
            with mock.patch.object(agent_trace, "PROJECTS_DIR", root), \
                    mock.patch.dict(os.environ, {agent_trace.SESSION_ID_ENV: ""}):
                self.assertIsNone(agent_trace.current_session_path())
                self.assertEqual(agent_trace.collect_sessions(args), [])


if __name__ == "__main__":
    unittest.main()
