#!/usr/bin/env python3
"""Block git commands that would create a branch or worktree other than main."""

from __future__ import annotations

import json
import re
import sys

BLOCK_PATTERNS = [
    (r"\bgit\s+checkout\s+-[bB]\b", "새 브랜치 생성(git checkout -b)"),
    (r"\bgit\s+switch\s+-c\b", "새 브랜치 생성(git switch -c)"),
    (r"\bgit\s+worktree\s+add\b", "git worktree 생성"),
    (
        r"\bgit\s+branch\s+(?!-[dDmMav]\b|--list\b)(?!$)(\S+)",
        "새 브랜치 생성(git branch)",
    ),
]

SWITCH_PATTERNS = [
    r"\bgit\s+checkout\s+(?!-[bB]\b|--\s)(\S+)",
    r"\bgit\s+switch\s+(?!-c\b)(\S+)",
]


def find_reason(command: str) -> str | None:
    for pattern, reason in BLOCK_PATTERNS:
        if re.search(pattern, command):
            return reason

    for pattern in SWITCH_PATTERNS:
        match = re.search(pattern, command)
        if match:
            target = match.group(1)
            if target not in ("main", "-"):
                return f"main이 아닌 브랜치로 전환({target})"

    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        print(json.dumps({}))
        return 0

    command = payload.get("tool_input", {}).get("command", "")
    if payload.get("tool_name") != "Bash":
        print(json.dumps({}))
        return 0

    reason = find_reason(command)
    if reason:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"이 레포는 main 브랜치만 사용한다 (CLAUDE.md 규칙). 감지된 동작: {reason}. "
                            "브랜치/워크트리 없이 main 체크아웃에서 직접 작업하세요."
                        ),
                    }
                },
                ensure_ascii=False,
            )
        )
        return 0

    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
