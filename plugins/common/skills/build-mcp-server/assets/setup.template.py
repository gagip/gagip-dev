#!/usr/bin/env python3
"""<서비스> MCP 서버의 자격 증명을 만든다.

이 스크립트는 사용자가 직접 실행한다. 입력한 값은 화면에 다시 출력하지 않고
곧바로 자격 증명 파일로 들어간다 — 에이전트의 대화 기록을 지나가지 않는다.

    python3 setup.py
"""

import getpass
import json
import os
import stat
import sys
import urllib.error
import urllib.request

DEFAULT_PATH = os.path.expanduser("~/.config/<서비스>/credentials.json")
VERIFY_URL = "https://api.example.com/v1/whoami"


def verify(token):
    """받은 값이 실제로 통하는지 저장 전에 확인한다. 안 그러면 처음 쓸 때 터진다."""
    req = urllib.request.Request(VERIFY_URL, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"자격 증명이 거절됐습니다 ({e.code}): {e.read().decode(errors='replace')[:200]}")


def main():
    path = os.environ.get("<PREFIX>_CREDENTIALS", DEFAULT_PATH)

    print("<서비스> MCP 자격 증명 설정")
    print("<발급 위치 안내 — 어느 화면에서 무엇을 복사해 오는지>\n")

    token = getpass.getpass("토큰 (입력해도 화면에 안 보입니다): ").strip()
    if not token:
        sys.exit("토큰이 필요합니다.")

    info = verify(token)
    print(f"\n확인: {info.get('account', '(계정 정보 없음)')}")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"token": token}, f, indent=2)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    print(f"저장했습니다: {path} (권한 600)")
    print("서버 코드 폴더 밖이라 폴더를 통째로 공유해도 따라가지 않습니다.")


if __name__ == "__main__":
    main()
