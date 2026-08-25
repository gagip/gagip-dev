#!/usr/bin/env python3
"""Pull the latest changes on session start."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", "pull", "--ff-only"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    print(json.dumps({"systemMessage": f"git pull: {output}"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
