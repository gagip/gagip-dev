#!/usr/bin/env python3
"""'지금 상태'를 단정하기 전에 PR·CI·태그·서버 응답을 읽기 전용으로 모아 시각과 함께 JSON으로 저장한다.

    python3 state_snapshot.py --out <파일> [--repo <레포>] [--pr <번호 또는 브랜치>] [--config <설정 파일>]

서버 URL은 레포 밖 설정 파일(기본 ~/.config/state-snapshot.json, {"servers": {"이름": "URL"}})에서 읽는다.
종료 코드: 전부 수집 0, 하나라도 수집 실패 1. 실패해도 나머지는 모두 수집한다.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

DEFAULT_CONFIG = Path("~/.config/state-snapshot.json").expanduser()
HTTP_TIMEOUT = 5
BODY_BYTES = 200
RECENT_TAGS = 5

# (인자 목록, 작업 폴더) -> (종료 코드, stdout, stderr)
Runner = Callable[[list[str], Path], tuple[int, str, str]]
# (URL, 제한 시간) -> {"status", "elapsed_ms", "body"}; 연결 실패는 예외
HttpGet = Callable[[str, float], dict]


def shell_runner(args: list[str], cwd: Path) -> tuple[int, str, str]:
    done = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=60)
    return done.returncode, done.stdout, done.stderr


def http_get(url: str, timeout: float) -> dict:
    started = time.monotonic()
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status, body = response.status, response.read(BODY_BYTES)
    except urllib.error.HTTPError as error:
        status, body = error.code, error.read(BODY_BYTES)
    return {"status": status, "elapsed_ms": round((time.monotonic() - started) * 1000),
            "body": body.decode("utf-8", errors="replace")}


def _failed(command: list[str], error: str) -> dict:
    return {"command": command, "ok": False, "error": error}


def _json_command(run: Runner, command: list[str], cwd: Path, accept_nonzero: bool = False) -> tuple[dict | None, dict | None]:
    """(파싱 결과, 실패 항목)을 돌려준다. `gh pr checks`는 실패·대기 중에도 0이 아닌 코드로 JSON을 낸다."""
    code, out, err = run(command, cwd)
    if code != 0 and not (accept_nonzero and out.strip()):
        return None, _failed(command, f"종료 코드 {code}: {err.strip() or out.strip()}")
    try:
        return json.loads(out), None
    except json.JSONDecodeError as error:
        return None, _failed(command, f"JSON 해석 실패: {error}")


def collect_pr(run: Runner, repo: Path, pr: str) -> dict:
    command = ["gh", "pr", "view", *([pr] if pr else []), "--json",
               "number,state,headRefName,headRefOid,mergedAt,url"]
    code, out, err = run(command, repo)
    if code != 0:
        if "no pull requests found" in err:
            return {"command": command, "ok": True, "result": None, "note": "이 브랜치에 PR 없음"}
        return _failed(command, f"종료 코드 {code}: {err.strip()}")
    try:
        return {"command": command, "ok": True, "result": json.loads(out)}
    except json.JSONDecodeError as error:
        return _failed(command, f"JSON 해석 실패: {error}")


def collect_ci(run: Runner, repo: Path, pr_item: dict) -> dict:
    pr = pr_item.get("result")
    if pr:
        command = ["gh", "pr", "checks", str(pr["number"]), "--json", "name,state,bucket,link"]
        data, failure = _json_command(run, command, repo, accept_nonzero=True)
    else:
        code, branch, err = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
        if code != 0:
            return _failed(["git", "rev-parse", "--abbrev-ref", "HEAD"], err.strip())
        command = ["gh", "run", "list", "--branch", branch.strip(), "--limit", "5", "--json",
                   "databaseId,status,conclusion,headSha,url"]
        data, failure = _json_command(run, command, repo)
    return failure or {"command": command, "ok": True, "result": data}


def _version_key(tag: str) -> list:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", tag)]


def collect_tags(run: Runner, repo: Path) -> dict:
    command = ["git", "ls-remote", "--tags", "origin"]
    code, out, err = run(command, repo)
    if code != 0:
        return _failed(command, f"종료 코드 {code}: {err.strip()}")
    tags = {}
    for line in out.splitlines():
        sha, _, ref = line.partition("\t")
        if ref.startswith("refs/tags/"):
            name = ref.removeprefix("refs/tags/").removesuffix("^{}")
            tags[name] = sha  # 주석 태그는 ^{} 줄의 커밋 해시가 뒤에 와서 덮어쓴다
    latest = sorted(tags, key=_version_key)[-RECENT_TAGS:]
    return {"command": command, "ok": True,
            "result": {"count": len(tags), "latest_by_version": [{"name": n, "sha": tags[n]} for n in latest]}}


def collect_servers(config: Path, get: HttpGet) -> dict[str, dict]:
    if not config.exists():
        return {"servers": {"command": [], "ok": True, "result": None, "note": "설정 없음"}}
    try:
        servers = json.loads(config.read_text(encoding="utf-8"))["servers"]
        if not isinstance(servers, dict):
            raise TypeError("servers는 {이름: URL} 객체여야 한다")
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {"servers": _failed([], f"설정 파일을 읽지 못했다: {error!r}")}
    items = {}
    for name, url in servers.items():
        command = ["GET", url]
        try:
            items[f"server:{name}"] = {"command": command, "ok": True, "result": get(url, HTTP_TIMEOUT)}
        except Exception as error:  # 연결·시간 초과·잘못된 URL 모두 항목 실패로 남기고 계속한다
            items[f"server:{name}"] = _failed(command, f"{type(error).__name__}: {error}")
    return items


def snapshot(repo: Path, pr: str, config: Path, run: Runner = shell_runner, get: HttpGet = http_get,
             now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> dict:
    pr_item = collect_pr(run, repo, pr)
    items = {"pr": pr_item, "ci": collect_ci(run, repo, pr_item), "tags": collect_tags(run, repo),
             **collect_servers(config, get)}
    return {"collected_at_utc": now().isoformat(timespec="seconds"), "repo": str(repo), "items": items}


def summary_line(name: str, item: dict) -> str:
    if not item["ok"]:
        return f"실패  {name}: {item['error']}"
    if item.get("note"):
        return f"정상  {name}: {item['note']}"
    return f"정상  {name}: {json.dumps(item['result'], ensure_ascii=False)[:160]}"


def main(argv: list[str] | None = None, run: Runner = shell_runner, get: HttpGet = http_get) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--pr", default="")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    result = snapshot(args.repo.resolve(), args.pr, args.config, run, get)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"수집 시각(UTC) {result['collected_at_utc']} → {args.out}")
    for name, item in result["items"].items():
        print(summary_line(name, item))
    return 0 if all(item["ok"] for item in result["items"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
