#!/usr/bin/env python3
"""MCP stdio 서버를 직접 두드려 본다.

등록만으로는 서버가 실제로 답하는지 알 수 없고, 이미 떠 있는 세션에는 새 등록이 붙지 않는다.
그래서 만든 직후 확인은 이 스크립트로 한다.

    probe.py <server.py> --list
    probe.py <server.py> <도구이름> [key=value ...]
    probe.py <server.py> <도구이름> --json '{"name": "값"}'

값은 숫자로 보이면 숫자로, true/false 는 불리언으로 넘긴다.
"""

import argparse
import json
import subprocess
import sys


def coerce(text):
    lowered = text.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def parse_pairs(pairs):
    args = {}
    for pair in pairs:
        if "=" not in pair:
            sys.exit(f"key=value 형식이 아닙니다: {pair}")
        key, _, value = pair.partition("=")
        args[key] = coerce(value)
    return args


def send(server, python, requests):
    payload = "\n".join(json.dumps(r, ensure_ascii=False) for r in requests) + "\n"
    proc = subprocess.run(
        [python, server], input=payload, capture_output=True, text=True, timeout=120
    )
    if proc.stderr.strip():
        print("[stderr]", proc.stderr.strip()[:1000], file=sys.stderr)

    out = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            print("[JSON 아님]", line[:200], file=sys.stderr)
    return out


def show(responses):
    failed = False
    for resp in responses:
        result = resp.get("result", {})
        if "serverInfo" in result:
            print(f"서버: {result['serverInfo']}  (프로토콜 {result.get('protocolVersion')})")
        elif "tools" in result:
            print(f"도구 {len(result['tools'])}개")
            for tool in result["tools"]:
                print(f"  - {tool['name']}: {tool.get('description', '')}")
        elif "content" in result:
            is_error = result.get("isError", False)
            failed = failed or is_error
            print(f"--- isError={is_error}")
            for block in result["content"]:
                print(block.get("text", ""))
        elif "error" in resp:
            failed = True
            print("[오류]", resp["error"])
    return failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("server")
    ap.add_argument("tool", nargs="?")
    ap.add_argument("pairs", nargs="*")
    ap.add_argument("--list", action="store_true", help="도구 목록만 본다")
    ap.add_argument("--json", dest="json_args", help="인자를 JSON 객체로 넘긴다")
    ap.add_argument("--python", default=sys.executable, help="서버를 실행할 파이썬")
    opts = ap.parse_args()

    requests = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}]
    if opts.list or not opts.tool:
        requests.append({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    else:
        args = json.loads(opts.json_args) if opts.json_args else parse_pairs(opts.pairs)
        requests.append({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": opts.tool, "arguments": args},
        })

    sys.exit(1 if show(send(opts.server, opts.python, requests)) else 0)


if __name__ == "__main__":
    main()
