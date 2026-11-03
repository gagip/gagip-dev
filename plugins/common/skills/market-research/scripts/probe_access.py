"""출처별 샘플 주소를 curl로 받아 보고, 자동으로 읽을 수 있는지 1차로 가른다.

    python3 probe_access.py --urls urls.tsv --out raw/access.tsv

urls.tsv 칸: source, url. 출력 칸 중 browser·extension은 비워 두고, 에이전트가 내장 브라우저·
브라우저 확장으로 같은 주소를 열어 본 결과(열림 / 정책 차단 / 로그인 요구)를 채운다.
curl verdict: 본문 있음 / 로그인·차단 화면 의심 / 받기 실패.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

from tsv_io import UA, read_tsv, write_tsv

LOGIN_URL_HINTS = r"login|signin|sign_in|nidlogin|auth"
BLOCK_HINTS = r"로그인|login|sign in|captcha|robot|접근이 제한|access denied|권한이 없|회원만|members only"
MIN_BODY_CHARS = 500
HEAD = ["source", "url", "http", "final_url", "text_chars", "curl", "browser", "extension"]


def visible_text(page: str) -> str:
    without_code = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", without_code)).strip()


def classify(http_code: str, text: str, final_url: str = "") -> str:
    if http_code != "200":
        return "받기 실패"
    visible = visible_text(text)
    if re.search(LOGIN_URL_HINTS, final_url, re.I):
        return "로그인·차단 화면 의심"
    if len(visible) < MIN_BODY_CHARS or (re.search(BLOCK_HINTS, visible, re.I) and len(visible) < MIN_BODY_CHARS * 4):
        return "로그인·차단 화면 의심"
    return "본문 있음"


def probe(url: str) -> tuple[str, str, str]:
    result = subprocess.run(["curl", "-sL", "-m", "20", "-A", UA, "-w", "\n%{http_code}\t%{url_effective}", url],
                            capture_output=True, text=True, errors="ignore")
    if result.returncode != 0:
        return "000", "", ""
    body, _, meta = result.stdout.rpartition("\n")
    code, _, final = meta.partition("\t")
    return code, final, body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--urls", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = []
    for row in read_tsv(args.urls):
        code, final, body = probe(row["url"])
        text_chars = len(visible_text(body).replace(" ", ""))
        verdict = classify(code, body, final)
        rows.append([row["source"], row["url"], code, final, str(text_chars), verdict, "", ""])
        print(f"{row['source']}: {verdict} (HTTP {code}, 글자 {text_chars})")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(args.out, HEAD, rows)
    print(f"→ {args.out} (browser·extension 칸은 직접 열어 보고 채운다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
