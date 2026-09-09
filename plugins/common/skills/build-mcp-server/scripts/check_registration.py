#!/usr/bin/env python3
"""여러 에이전트 하네스에 같은 MCP 서버가 같은 명령으로 등록됐는지 대조한다.

두 도구를 번갈아 쓰면 등록도 두 곳에 따로 해야 하고, 한쪽만 하면 반대쪽에서 조용히
없는 채로 남는다. 이 스크립트는 각 하네스의 설정을 읽기만 하고 고치지 않는다 —
설정은 실행 중인 프로세스가 덮어쓰므로 반드시 각 도구의 mcp 명령으로 바꾼다.

    check_registration.py [이름 ...]     이름을 주면 그 서버만 본다
"""

import json
import os
import sys

CONFIGS = {
    "claude": os.path.expanduser("~/.claude.json"),
    "codex": os.path.expanduser("~/.codex/config.toml"),
}

# 하네스가 스스로 관리해 사람이 맞출 필요가 없는 항목은 대조에서 뺀다.
IGNORED = {"node_repl", "computer-use", "cua_repl", "event-stream"}


def load_claude(path):
    with open(path) as f:
        servers = json.load(f).get("mcpServers", {})
    return {
        name: " ".join([spec.get("command", "")] + list(spec.get("args", []))).strip()
        for name, spec in servers.items()
    }


def load_codex(path):
    try:
        import tomllib
    except ModuleNotFoundError:
        sys.exit("codex 설정을 읽으려면 Python 3.11 이상이 필요합니다.")
    with open(path, "rb") as f:
        servers = tomllib.load(f).get("mcp_servers", {})
    return {
        name: " ".join([spec.get("command", "")] + list(spec.get("args", []))).strip()
        for name, spec in servers.items()
    }


LOADERS = {"claude": load_claude, "codex": load_codex}


def main():
    wanted = set(sys.argv[1:])

    found = {}
    for harness, path in CONFIGS.items():
        if not os.path.exists(path):
            print(f"[건너뜀] {harness}: 설정 파일 없음 ({path})")
            continue
        entries = LOADERS[harness](path)
        found[harness] = {k: v for k, v in entries.items() if k not in IGNORED}

    if len(found) < 2:
        print("대조할 하네스가 둘 미만입니다.")
        return 0

    problems = 0
    names = set().union(*found.values())
    if wanted:
        names &= wanted
        for missing in sorted(wanted - names):
            problems += 1
            print(f"[없음] {missing}: 어느 하네스에도 등록되지 않았습니다.")

    for name in sorted(names):
        commands = {h: found[h].get(name) for h in found}
        absent = [h for h, c in commands.items() if c is None]
        if absent:
            problems += 1
            print(f"[누락] {name}: {', '.join(absent)} 에 없음")
            continue
        if len(set(commands.values())) > 1:
            problems += 1
            print(f"[불일치] {name}")
            for harness, command in commands.items():
                print(f"    {harness}: {command}")
            continue
        print(f"[일치] {name}: {next(iter(commands.values()))}")

    if problems:
        print(f"\n{problems}건 어긋남 — 각 도구의 mcp 명령으로 맞추세요 (설정 파일 직접 편집 금지).")
    else:
        print(f"\n{len(names)}개 서버 전부 일치")
    # 어긋난 게 있으면 1 로 끝난다 — CI·훅에서 그대로 실패로 쓸 수 있게.
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
