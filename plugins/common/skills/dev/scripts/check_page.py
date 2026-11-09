# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright==1.64.1"]
# ///
"""HTML 페이지를 설치된 Chrome으로 열어 앵커·링크·이미지·콘솔 오류·도착 주소를 검사한다.

사용: uv run check_page.py <경로|URL> --shots <저장 폴더>
종료 코드: 0 통과(미확인만 있어도 0), 1 실패 항목 있음, 2 검사 자체를 못 함.
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

OK, FAIL, UNCHECKED = "통과", "실패", "미확인"
EXTERNAL_TIMEOUT_SECONDS = 10
MAX_REDIRECTS = 5
# 봇 차단·속도 제한 응답은 링크가 깨졌다는 증거가 아니다.
BOT_BLOCK_STATUSES = {401, 403, 429, 999}

COLLECT_JS = """() => ({
  links: [...document.querySelectorAll('a[href]')].map(a => ({raw: a.getAttribute('href'), abs: a.href})),
  ids: [...document.querySelectorAll('[id], a[name]')].map(e => e.id || e.getAttribute('name')),
  brokenImages: [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.currentSrc || i.src),
})"""


@dataclass(frozen=True)
class Result:
    category: str
    status: str
    detail: str


def exit_code(results: list[Result]) -> int:
    return 1 if any(r.status == FAIL for r in results) else 0


def host_key(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").removeprefix("www.")


def check_anchor(raw: str, ids: set[str]) -> Result:
    require(raw.startswith("#"), f"앵커 href가 아니다: {raw}")
    name = urllib.parse.unquote(raw[1:])
    if name in ("", "top") or name in ids:
        return Result("앵커", OK, raw)
    return Result("앵커", FAIL, f"{raw} 대상 id가 문서에 없다")


def check_local_file(url: str) -> Result:
    path = Path(urllib.request.url2pathname(urllib.parse.urlsplit(url).path))
    if path.exists():
        return Result("로컬 링크", OK, str(path))
    return Result("로컬 링크", FAIL, f"{path} 파일이 없다")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch_final(url: str) -> tuple[int, str]:
    """리다이렉트를 직접 따라가 (최종 상태 코드, 최종 주소)를 돌려준다. 네트워크 실패는 OSError."""
    opener = urllib.request.build_opener(_NoRedirect)
    for _ in range(MAX_REDIRECTS + 1):
        request = urllib.request.Request(url, headers={"User-Agent": "check_page/1"})
        try:
            with opener.open(request, timeout=EXTERNAL_TIMEOUT_SECONDS) as response:
                return response.status, url
        except urllib.error.HTTPError as error:
            location = error.headers.get("Location")
            if error.code in (301, 302, 303, 307, 308) and location:
                url = urllib.parse.urljoin(url, location)
                continue
            return error.code, url
    raise OSError("리다이렉트가 너무 많다")


def check_external(url: str) -> Result:
    last_error = ""
    for _ in range(2):  # 첫 시도 + 재시도 1번
        try:
            status, final = fetch_final(url)
        except (OSError, ValueError) as error:  # URLError·타임아웃·소켓 오류
            last_error = str(error)
            continue
        if host_key(final) != host_key(url):
            return Result("외부 링크", FAIL, f"{url} 이(가) 다른 도메인 {final} 으로 넘어간다")
        if status in BOT_BLOCK_STATUSES:
            return Result("외부 링크", UNCHECKED, f"{url} 응답 {status}(차단 가능성)")
        if status >= 400:
            return Result("외부 링크", FAIL, f"{url} 응답 {status}")
        return Result("외부 링크", OK, f"{url} {status}")
    return Result("외부 링크", UNCHECKED, f"{url} 네트워크 실패: {last_error}")


def classify_link(raw: str, absolute: str, page_url: str, ids: set[str]) -> Result | None:
    """링크 하나를 판정한다. 검사 대상이 아닌 스킴(mailto 등)은 None."""
    if raw.startswith("#"):
        return check_anchor(raw, ids)
    scheme = urllib.parse.urlsplit(absolute).scheme
    if scheme == "file":
        return check_local_file(absolute)
    if scheme in ("http", "https"):
        if urllib.parse.urldefrag(absolute).url == urllib.parse.urldefrag(page_url).url:
            return check_anchor("#" + urllib.parse.urlsplit(absolute).fragment, ids)
        return check_external(absolute)
    return None


def to_url(target: str) -> str:
    if urllib.parse.urlsplit(target).scheme in ("http", "https", "file"):
        return target
    path = Path(target).expanduser().resolve()
    require(path.exists(), f"파일이 없다: {path}")
    return path.as_uri()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def shot_name(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    stem = Path(parts.path).stem or parts.hostname or "page"
    return f"{stem}.png"


def inspect_page(url: str, shots: Path) -> tuple[list[Result], Path]:
    from playwright.sync_api import sync_playwright

    console_errors: list[str] = []
    results: list[Result] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        page = browser.new_page()
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(f"예외: {e}"))
        page.goto(url, wait_until="load")
        page.wait_for_load_state("networkidle")
        found = page.evaluate(COLLECT_JS)
        final_url = page.url
        shots.mkdir(parents=True, exist_ok=True)
        shot = (shots / shot_name(url)).resolve()
        page.screenshot(path=str(shot), full_page=True)
        browser.close()

    ids = set(found["ids"])
    if urllib.parse.urlsplit(url).scheme in ("http", "https") and host_key(final_url) != host_key(url):
        results.append(Result("도착 주소", FAIL, f"{url} 이(가) 다른 도메인 {final_url} 으로 넘어갔다"))
    else:
        results.append(Result("도착 주소", OK, final_url))
    seen: set[tuple[str, str]] = set()
    for link in found["links"]:
        key = (link["raw"], link["abs"])
        if key in seen:
            continue
        seen.add(key)
        result = classify_link(link["raw"], link["abs"], final_url, ids)
        if result is not None:
            results.append(result)
    results += [Result("이미지", FAIL, f"{src} 로드 실패") for src in found["brokenImages"]]
    if not found["brokenImages"]:
        results.append(Result("이미지", OK, "깨진 이미지 없음"))
    results += [Result("콘솔 오류", FAIL, text) for text in console_errors]
    if not console_errors:
        results.append(Result("콘솔 오류", OK, "콘솔 error·페이지 예외 없음"))
    return results, shot


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="로컬 HTML 경로 또는 URL")
    parser.add_argument("--shots", required=True, type=Path, help="전체 페이지 캡처를 저장할 폴더")
    args = parser.parse_args(argv)
    try:
        results, shot = inspect_page(to_url(args.target), args.shots)
    except Exception as error:  # 브라우저 실행·페이지 열기 실패는 검사 불가로 따로 알린다
        print(f"검사 불가: {error}", file=sys.stderr)
        return 2
    for r in results:
        print(f"[{r.status}] {r.category}: {r.detail}")
    print(f"캡처: {shot}")
    unchecked = sum(r.status == UNCHECKED for r in results)
    failed = sum(r.status == FAIL for r in results)
    print(f"실패 {failed}개, 미확인 {unchecked}개")
    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
