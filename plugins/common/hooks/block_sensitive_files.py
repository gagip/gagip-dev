#!/usr/bin/env python3
"""PreToolUse hook: block edits to sensitive files.

.env, 키, 인증서 등 민감한 파일에 대한 Edit/Write를 차단한다.
"""

import json
import os
import sys


BLOCKED_EXTENSIONS = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}
BLOCKED_PATTERNS = ["secrets", "credentials", "service-account"]


def is_sensitive(file_path: str) -> bool:
    basename = os.path.basename(file_path).lower()
    _, ext = os.path.splitext(basename)

    if basename.startswith(".env"):
        return True
    if ext in BLOCKED_EXTENSIONS:
        return True
    if any(pattern in basename for pattern in BLOCKED_PATTERNS):
        return True
    return False


def main():
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name not in ("Edit", "Write"):
        print(json.dumps({}))
        sys.exit(0)

    file_path = input_data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        print(json.dumps({}))
        sys.exit(0)

    if is_sensitive(file_path):
        message = (
            f"🚫 민감한 파일 편집이 차단되었습니다: '{file_path}'\n"
            "이 파일을 수정해야 한다면 사용자에게 직접 편집을 요청하세요."
        )
        print(json.dumps({"decision": "block", "reason": message}))
        sys.exit(0)

    print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    main()
