#!/usr/bin/env python3
"""Block Claude Code git commits when repository metadata has drifted."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        print(json.dumps({}))
        return 0

    command = payload.get("tool_input", {}).get("command", "")
    if payload.get("tool_name") != "Bash" or not re.search(r"\bgit\s+commit\b", command):
        print(json.dumps({}))
        return 0

    root = Path(__file__).resolve().parents[2]
    check = subprocess.run(
        [sys.executable, str(root / "scripts" / "check_consistency.py")],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if check.returncode:
        reason = (check.stdout + check.stderr).strip()
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
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
