#!/usr/bin/env python3
"""<서비스> 목적별 수집 MCP 서버 (표준 라이브러리만 사용).

허용 목록에 없는 항목은 읽을 수 없다. 목록 조회와 상세 조회 두 경로 모두에서 막는다 —
목록만 막으면 다른 데서 알아낸 ID로 상세를 열 수 있다.

쓰기 도구는 없다. 이 서버로는 아무것도 바꿀 수 없다.

환경변수:
    <PREFIX>_CREDENTIALS  자격 증명 파일 경로 (기본 ~/.config/<서비스>/credentials.json)
    <PREFIX>_ALLOWED      허용 항목, 쉼표 구분 (기본 아래 DEFAULT_ALLOWED)
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_ALLOWED = []  # 예: ["알림-채널", "배포-로그"]
CRED_PATH = os.environ.get(
    "<PREFIX>_CREDENTIALS", os.path.expanduser("~/.config/<서비스>/credentials.json")
)
API = "https://api.example.com/v1"

SERVER_NAME = "<서비스>"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"


class Blocked(Exception):
    """사용자에게 그대로 보여줄 오류. 서버를 죽이지 않는다."""


def allowed_names():
    raw = os.environ.get("<PREFIX>_ALLOWED")
    names = raw.split(",") if raw else DEFAULT_ALLOWED
    return [n.strip() for n in names if n.strip()]


# --- 인증 -------------------------------------------------------------------

def credentials():
    try:
        with open(CRED_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        raise Blocked(
            f"자격 증명이 없습니다: {CRED_PATH}\n"
            "서버 폴더에서 `python3 setup.py` 를 실행해 만드세요."
        )


def api_get(path, params=None):
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    token = credentials()["token"]
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise Blocked("호출 한도에 걸렸습니다. 잠시 뒤 다시 시도하세요.")
        raise Blocked(f"API 오류 ({e.code}): {e.read().decode(errors='replace')[:300]}")


# --- 허용 목록 --------------------------------------------------------------

def allowed_index():
    """허용 항목 중 실제로 존재하는 것만 {이름: 정보} 로 돌려준다."""
    wanted = {n.lower() for n in allowed_names()}
    return {
        item["name"]: item
        for item in api_get("/items").get("items", [])
        if item["name"].lower() in wanted
    }


def resolve(name):
    """허용된 항목이면 정보를, 아니면 막는다. 외부 식별자를 받는 도구는 전부 여기를 지난다."""
    idx = allowed_index()
    match = next((n for n in idx if n.lower() == name.lower()), None)
    if not match:
        raise Blocked(
            f"'{name}' 은 허용된 항목이 아닙니다. 허용: {', '.join(idx) or '(없음)'}"
        )
    return idx[match]


# --- 도구 구현 --------------------------------------------------------------

def tool_list_allowed():
    idx = allowed_index()
    missing = [n for n in allowed_names() if n not in idx]
    lines = [f"허용 항목 {len(idx)}개:"] + [f"  - {n}" for n in idx]
    if missing:
        lines += ["", "설정엔 있으나 못 찾은 항목: " + ", ".join(missing)]
    return "\n".join(lines)


def tool_fetch(name, limit=20):
    item = resolve(name)
    limit = max(1, min(int(limit), 100))
    data = api_get(f"/items/{item['id']}/entries", {"limit": limit})
    entries = data.get("entries", [])
    if not entries:
        return f"'{item['name']}' 에 최근 항목이 없습니다."
    return "\n".join([f"'{item['name']}' · {len(entries)}건", ""] + [render(e) for e in entries])


def render(entry):
    # 본문이 최상위가 아니라 첨부·블록 안쪽에 있는 형식이 흔하다. 실제 응답을 떠서
    # 픽스처로 박고, 자리표시자가 본문으로 새지 않는지 테스트로 확인한다.
    return f"[{entry.get('created_at', '')}] {entry.get('author', '(알 수 없음)')}\n   {entry.get('text', '')}"


TOOLS = [
    {
        "name": "list_allowed",
        "description": "조회가 허용된 항목 목록을 돌려준다. 다른 항목은 이 서버로 볼 수 없다.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda a: tool_list_allowed(),
    },
    {
        "name": "fetch",
        "description": "허용된 항목의 최근 기록을 돌려준다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "허용 항목 이름"},
                "limit": {"type": "integer", "description": "최대 건수 (기본 20, 상한 100)"},
            },
            "required": ["name"],
        },
        "handler": lambda a: tool_fetch(a["name"], a.get("limit", 20)),
    },
]


# --- MCP stdio 루프 ---------------------------------------------------------

def handle(req):
    method = req.get("method")

    if method == "initialize":
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }

    if method == "tools/list":
        return {"tools": [{k: t[k] for k in ("name", "description", "inputSchema")} for t in TOOLS]}

    if method == "tools/call":
        params = req.get("params", {})
        tool = next((t for t in TOOLS if t["name"] == params.get("name")), None)
        if not tool:
            raise Blocked(f"알 수 없는 도구: {params.get('name')}")
        return {"content": [{"type": "text", "text": tool["handler"](params.get("arguments") or {})}]}

    raise Blocked(f"지원하지 않는 메서드: {method}")


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        if req.get("method", "").startswith("notifications/"):
            continue

        try:
            result = {"jsonrpc": "2.0", "id": req.get("id"), "result": handle(req)}
        except Blocked as e:
            result = {
                "jsonrpc": "2.0",
                "id": req.get("id"),
                "result": {"content": [{"type": "text", "text": str(e)}], "isError": True},
            }
        except Exception as e:  # 서버가 죽으면 도구 전체가 사라지므로 삼킨다
            result = {
                "jsonrpc": "2.0",
                "id": req.get("id"),
                "result": {"content": [{"type": "text", "text": f"내부 오류: {e}"}], "isError": True},
            }

        sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
