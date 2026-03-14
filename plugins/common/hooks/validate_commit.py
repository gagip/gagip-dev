#!/usr/bin/env python3
"""PreToolUse hook: validate commit message convention before committing.

커밋 명령 실행 전 커밋 메시지가 컨벤션을 따르는지 검증하고, 위반 시 차단한다.
형식: <type>: <요약>
허용 type: feat, fix, refactor, style, test, docs, chore, ai
"""

import json
import re
import sys


VALID_TYPES = {"feat", "fix", "refactor", "style", "test", "docs", "chore", "ai"}
CONVENTION_PATTERN = re.compile(
    r"^(" + "|".join(VALID_TYPES) + r")(\(.+\))?: .+$"
)


def is_commit_command(command: str) -> bool:
    """git commit 명령인지 확인한다."""
    return "git commit" in command and "--no-verify" not in command


def extract_commit_message(command: str) -> str | None:
    """-m 플래그 또는 HEREDOC에서 커밋 메시지 첫 줄을 추출한다."""
    # HEREDOC 패턴 우선: -m "$(cat <<'EOF' ... EOF)" 또는 cat <<'EOF' ... EOF
    m = re.search(r"cat\s+<<'?EOF'?\s*\n(.*?)\nEOF", command, re.DOTALL)
    if m:
        first_line = m.group(1).strip().splitlines()[0]
        return first_line.strip()

    # -m "..." 또는 -m '...' 패턴
    m = re.search(r'-m\s+["\']([^\n"\']+)', command)
    if m:
        return m.group(1).strip()

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

    subject = extract_commit_message(command)
    if not subject:
        # 메시지를 추출할 수 없으면 통과 (interactive 커밋 등)
        print(json.dumps({}))
        sys.exit(0)

    if not CONVENTION_PATTERN.match(subject):
        message = (
            f"커밋 메시지 컨벤션 위반: '{subject}'\n"
            f"형식: <type>: <요약> (예: feat: 로그인 기능 추가)\n"
            f"허용 type: {', '.join(sorted(VALID_TYPES))}"
        )
        print(json.dumps({"decision": "block", "reason": message}))
    else:
        print(json.dumps({}))

    sys.exit(0)


if __name__ == "__main__":
    main()
