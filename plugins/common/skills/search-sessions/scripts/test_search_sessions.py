#!/usr/bin/env python3
"""search-sessions.py를 가짜 HOME의 세션 로그로 실행해 출력을 검증한다."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search-sessions.py")
TS = "2026-01-02T03:04:05Z"


def user(text, **extra):
    return {"type": "user", "timestamp": TS, "cwd": "/work/app",
            "message": {"content": text}, **extra}


def queued(prompt, mode="prompt", **extra):
    return {"type": "attachment", "timestamp": TS, "cwd": "/work/app",
            "attachment": {"type": "queued_command", "commandMode": mode,
                           "prompt": prompt, **extra}}


class SearchSessionsTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        self.folder = os.path.join(self.home.name, ".claude", "projects", "app")
        os.makedirs(self.folder)

    def write_log(self, name, records):
        path = os.path.join(self.folder, name)
        with open(path, "w", encoding="utf-8") as log:
            for record in records:
                log.write(json.dumps(record, ensure_ascii=False) + "\n")
        return path

    def search(self, *args):
        result = subprocess.run(
            [sys.executable, SCRIPT, *args],
            capture_output=True, text=True, check=True,
            env={**os.environ, "HOME": self.home.name},
        )
        return result.stdout

    def test_mid_turn_user_message_is_found_with_user_role(self):
        self.write_log("a.jsonl", [queued("삭제가 낫다")])

        output = self.search("삭제가", "--role", "user")

        self.assertIn("세션 1개 · 발화 1건", output)
        self.assertIn("/work/app", output)

    def test_block_list_prompt_is_found(self):
        self.write_log("a.jsonl", [queued([{"type": "text", "text": "목록 프롬프트"}])])

        self.assertIn("발화 1건", self.search("목록"))

    def test_non_user_queue_entries_are_ignored(self):
        self.write_log("a.jsonl", [
            queued("백그라운드 알림", mode="task-notification"),
            queued("주입된 알림", isMeta=True, origin={"kind": "peer"}),
        ])

        self.assertIn("일치하는 대화가 없다", self.search("알림"))

    def test_injected_user_record_is_ignored(self):
        self.write_log("a.jsonl", [user("스킬 본문", isMeta=True), user("스킬 질문")])

        self.assertIn("발화 1건", self.search("스킬"))

    def test_all_terms_must_be_in_one_message(self):
        self.write_log("a.jsonl", [user("브랜치 전략"), user("브랜치 삭제")])

        self.assertIn("발화 1건", self.search("브랜치", "전략"))

    def test_first_term_ignores_ascii_case(self):
        self.write_log("a.jsonl", [user("Worktree 정리")])

        self.assertIn("발화 1건", self.search("worktree"))

    def test_days_excludes_files_by_modified_time(self):
        now = datetime.now(timezone.utc).isoformat()
        self.write_log("recent.jsonl", [user("최근 결정", timestamp=now)])
        old = self.write_log("old.jsonl", [user("오래된 결정", timestamp=now)])
        os.utime(old, (0, 0))

        output = self.search("결정", "--days", "1")

        self.assertIn("세션 1개 · 발화 1건", output)
        self.assertIn("최근 결정", output)

    def test_codex_agent_message_is_assistant(self):
        folder = os.path.join(self.home.name, ".codex", "sessions")
        os.makedirs(folder)
        record = {"type": "event", "timestamp": TS, "payload": {
            "type": "item_completed",
            "item": {"type": "AgentMessage", "content": [{"type": "Text", "text": "중간 설명"}]},
        }}
        with open(os.path.join(folder, "rollout-a.jsonl"), "w", encoding="utf-8") as log:
            log.write(json.dumps(record, ensure_ascii=False) + "\n")

        output = self.search("중간", "--tool", "codex", "--role", "assistant")

        self.assertIn("발화 1건", output)

    def test_files_only_reports_message_count(self):
        path = self.write_log("a.jsonl", [user("한 건"), user("두 건")])

        output = self.search("건", "--files-only")

        self.assertIn(path, output)
        self.assertIn("세션 1개 · 발화 2건", output)


if __name__ == "__main__":
    unittest.main()
