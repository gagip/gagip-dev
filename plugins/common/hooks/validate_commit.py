#!/usr/bin/env python3
"""PostToolUse hook: validate commit message convention.

커밋 명령 실행 후 커밋 메시지가 컨벤션을 따르는지 검증한다.
형식: <type>: <요약>
허용 type: feat, fix, refactor, style, test, docs, chore, ai
"""

import json
import re
import subprocess
import sys


VALID_TYPES = {"feat", "fix", "refactor", "style", "test", "docs", "chore", "ai"}
CONVENTION_PATTERN = re.compile(
    r"^(" + "|".join(VALID_TYPES) + r")(\(.+\))?: .+$"
)


def is_commit_command(command: str) -> bool:
    """git commit 명령인지 확인한다."""
    return "git commit" in command and "--no-verify" not in command


def get_last_commit_message() -> str | None:
    """가장 최근 커밋 메시지의 첫 줄을 반환한다."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%s"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def main():
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        print(json.dumps({}))
        sys.exit(0)

    command = input_data.get("tool_input", {}).get("command", "")
    if not is_commit_command(command):
        print(json.dumps({}))
        sys.exit(0)

    # 커밋 성공 여부 확인 (is_error가 True면 커밋 실패)
    is_error = input_data.get("tool_response", {}).get("is_error", False)
    if is_error:
        print(json.dumps({}))
        sys.exit(0)

    subject = get_last_commit_message()
    if not subject:
        print(json.dumps({}))
        sys.exit(0)

    if not CONVENTION_PATTERN.match(subject):
        message = (
            f"⚠️ 커밋 메시지 컨벤션 위반: '{subject}'\n"
            f"형식: <type>: <요약> (예: feat: 로그인 기능 추가)\n"
            f"허용 type: {', '.join(sorted(VALID_TYPES))}"
        )
        print(json.dumps({"systemMessage": message}))
    else:
        print(json.dumps({}))

    sys.exit(0)


if __name__ == "__main__":
    main()
