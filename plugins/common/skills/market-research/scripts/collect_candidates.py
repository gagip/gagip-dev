"""검색 결과 페이지에서 후보 글 링크와 주변 글자를 뽑아 candidates.tsv로 모은다.

글 본문은 열지 않는다. 검색 결과 페이지만 받고, 받은 페이지는 원본 그대로 저장한다.

    # 검색어 파일로 받아서 뽑기 (queries.tsv 칸: group, query, source)
    python3 collect_candidates.py --queries queries.tsv --out raw/candidates

    # 이미 저장된 검색 결과 페이지에서 뽑기 (사람이 저장한 페이지, 다시 뽑기)
    python3 collect_candidates.py --from-html raw/pages --source naver_cafe --group Q1 --out raw/candidates

    # 프리셋에 없는 출처
    python3 collect_candidates.py --queries q.tsv --out raw/c \
        --search-url 'https://example.com/search?q={query}' --link-pattern 'https://example\\.com/post/\\d+'
"""
import argparse
import html
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

from tsv_io import UA, read_tsv, write_tsv

NAVER_DROP = r"\s*새 창 열림\s*$"

PRESETS = {
    "naver_cafe": {
        "search_url": "https://search.naver.com/search.naver?ssc=tab.cafe.all&query={query}",
        "link_pattern": r"https://cafe\.naver\.com/[A-Za-z0-9_]+/\d+",
        "drop_text": NAVER_DROP,
    },
    "naver_blog": {
        "search_url": "https://search.naver.com/search.naver?ssc=tab.blog.all&query={query}",
        "link_pattern": r"https://blog\.naver\.com/[A-Za-z0-9_\-]+/\d+",
        "drop_text": NAVER_DROP,
    },
    "naver_kin": {
        "search_url": "https://search.naver.com/search.naver?ssc=tab.kin.all&query={query}",
        "link_pattern": r"https://kin\.naver\.com/qna/detail\.naver\?[^\"'#\s]*docId=\d+",
        "drop_text": NAVER_DROP,
        "canonical": (r"dirId=(\d+).*?docId=(\d+)", "https://kin.naver.com/qna/detail.naver?dirId={0}&docId={1}"),
    },
}

HEAD = ["group", "query", "source", "url", "texts", "page"]
MIN_TEXT = 4
TEXTS_KEPT = 3


def clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def extract(page: str, link_pattern: str, drop_text: str = "", canonical: tuple[str, str] | None = None) -> list[dict]:
    """페이지의 a 태그 중 link_pattern에 맞는 것을 URL별로 묶고, 묶인 글자를 길이순으로 남긴다.

    canonical은 (정규식, 주소 틀)이다. 같은 글을 가리키는 여러 주소(답변 링크 등)를 한 주소로 모은다.
    """
    found: dict[str, list[str]] = {}
    for attrs, inner in re.findall(r"<a\b([^>]*)>(.*?)</a>", page, re.S):
        match = re.search(r'href="(' + link_pattern + ")", attrs)
        if not match:
            continue
        url = html.unescape(match.group(1))
        if canonical:
            key = re.search(canonical[0], url)
            url = canonical[1].format(*key.groups()) if key else url
        text = clean(inner)
        if drop_text:
            text = re.sub(drop_text, "", text).strip()
        found.setdefault(url, [])
        if len(text) >= MIN_TEXT and text not in found[url]:
            found[url].append(text)
    return [{"url": url, "texts": sorted(texts, key=len, reverse=True)[:TEXTS_KEPT]} for url, texts in found.items()]


def fetch(url: str, target: Path) -> str | None:
    """검색 결과 페이지를 받아 저장한다. 실패하면 오류 문장을 돌려준다."""
    result = subprocess.run(["curl", "-sL", "-m", "20", "-A", UA, "-o", str(target), "-w", "%{http_code}", url],
                            capture_output=True, text=True)
    if result.returncode != 0:
        return f"curl 실패(코드 {result.returncode})"
    if result.stdout.strip() != "200":
        return f"HTTP {result.stdout.strip()}"
    return None


def resolve(args, source: str) -> dict:
    if args.search_url or args.link_pattern:
        if not args.link_pattern:
            raise SystemExit("--search-url을 쓰면 --link-pattern도 줘야 한다")
        return {"search_url": args.search_url or "", "link_pattern": args.link_pattern, "drop_text": args.drop_text or ""}
    if source not in PRESETS:
        raise SystemExit(f"프리셋에 없는 출처: {source!r}. 프리셋: {', '.join(PRESETS)} 또는 --search-url/--link-pattern")
    return PRESETS[source]


def merge(row: list[str], group: str, query: str) -> None:
    """같은 글이 다른 질문·검색어에도 걸리면 group·query 칸에 |로 더한다."""
    for index, value in ((0, group), (1, query)):
        values = row[index].split("|") if row[index] else []
        if value and value not in values:
            row[index] = "|".join(values + [value])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--queries", type=Path, help="검색어 TSV(칸: group, query, source)")
    parser.add_argument("--from-html", type=Path, help="이미 저장된 검색 결과 페이지(*.html)가 있는 폴더")
    parser.add_argument("--source", default="", help="--from-html일 때 출처 프리셋 이름")
    parser.add_argument("--group", default="", help="--from-html일 때 후보에 붙일 질문·주제")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--search-url", help="프리셋 대신 쓸 검색 주소. {query} 자리에 검색어가 들어간다")
    parser.add_argument("--link-pattern", help="후보 글 링크 정규식")
    parser.add_argument("--drop-text", help="링크 글자에서 지울 정규식")
    parser.add_argument("--delay", type=float, default=1.5, help="검색 요청 사이 대기 초")
    args = parser.parse_args()
    if bool(args.queries) == bool(args.from_html):
        raise SystemExit("--queries와 --from-html 중 하나만 준다")

    args.out.mkdir(parents=True, exist_ok=True)
    rows: dict[str, list[str]] = {}
    report: list[str] = []

    def add(group: str, query: str, source: str, page_path: Path, preset: dict) -> None:
        items = extract(page_path.read_text(encoding="utf-8", errors="ignore"), preset["link_pattern"],
                        preset["drop_text"], preset.get("canonical"))
        new = [i for i in items if i["url"] not in rows]
        for item in items:
            if item["url"] in rows:
                merge(rows[item["url"]], group, query)
            else:
                rows[item["url"]] = [group, query, source, item["url"], " ‖ ".join(item["texts"]), page_path.name]
        note = " ← 0건: 저장된 페이지를 열어 차단·로그인 화면인지, 링크 패턴이 틀렸는지 확인" if not items else ""
        report.append(f"{page_path.name} {source} {query}: 링크 {len(items)}건, 새 후보 {len(new)}건{note}")

    if args.from_html:
        preset = resolve(args, args.source)
        for page_path in sorted(args.from_html.glob("*.html")):
            add(args.group, page_path.stem, args.source or "custom", page_path, preset)
    else:
        queries = read_tsv(args.queries)
        for n, row in enumerate(queries, 1):
            source = row.get("source", "").strip() or "custom"
            preset = resolve(args, source)
            url = preset["search_url"].format(query=urllib.parse.quote(row["query"]))
            target = args.out / f"{n:03d}_{source}.html"
            error = fetch(url, target)
            if error:
                report.append(f"{target.name} {source} {row['query']}: 받기 실패 {error}")
            else:
                add(row.get("group", ""), row["query"], source, target, preset)
            if n < len(queries):
                time.sleep(args.delay)

    write_tsv(args.out / "candidates.tsv", HEAD, list(rows.values()))
    print("\n".join(report))
    print(f"후보 {len(rows)}건 → {args.out / 'candidates.tsv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
