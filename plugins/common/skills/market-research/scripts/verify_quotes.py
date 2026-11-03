"""사례 파일의 인용 조각이 저장된 원문에 실제로 있는지 대조한다.

    python3 verify_quotes.py raw/cases.json
    python3 verify_quotes.py raw/cases.json --sample 2   # 스크린샷 판독 사례 중 직접 대조할 것 고르기

cases.json은 사례 목록이다. 사례마다 id, source(cases.json 기준 상대 경로 또는 URL), quotes(인용 조각 목록),
evidence(원문 저장 / 스크린샷 판독 / 직접 대조)를 둔다. source가 URL이면 받아서 _verify_cache/에 저장한다.
띄어쓰기·따옴표 모양 차이는 무시하고 글자가 같은지만 본다.
출력: 입력 파일 옆 verify_<입력 파일 이름>.tsv(예: verify_cases.tsv, verify_facts.tsv).
일치가 아닌 것(불일치·원문 없음·인용 없음·너무 짧음)이 하나라도 있으면 종료 코드 1.
"""
import argparse
import html
import json
import random
import re
import subprocess
import sys
from pathlib import Path

from tsv_io import UA, write_tsv

CAPTURE_EVIDENCE = "스크린샷 판독"
MIN_QUOTE_CHARS = 4
QUOTE_MARKS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "「": '"', "」": '"', "…": "..."})


def normalize(text: str) -> str:
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", text, flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", "", text.translate(QUOTE_MARKS)).lower()


def load_source(case: dict, base: Path, cache: Path) -> str | None:
    source = case.get("source", "")
    if re.match(r"https?://", source):
        cache.mkdir(exist_ok=True)
        target = cache / (re.sub(r"[^A-Za-z0-9_-]", "_", case["id"]) + ".html")
        if not target.exists():
            result = subprocess.run(["curl", "-sL", "-m", "20", "-A", UA, "-o", str(target), source])
            if result.returncode != 0 or not target.exists():
                return None
        return target.read_text(encoding="utf-8", errors="ignore")
    path = base / source
    return path.read_text(encoding="utf-8", errors="ignore") if source and path.is_file() else None


def verify(cases: list[dict], base: Path) -> list[list[str]]:
    rows = []
    for case in cases:
        if not case.get("id") or not isinstance(case.get("quotes"), list):
            raise ValueError(f"사례에 id나 quotes 목록이 없다: {case}")
        text = load_source(case, base, base / "_verify_cache")
        haystack = normalize(text) if text is not None else None
        if not case["quotes"]:
            rows.append([case["id"], "0", "인용 없음", case.get("evidence", ""), ""])
        for n, quote in enumerate(case["quotes"], 1):
            if len(normalize(quote)) < MIN_QUOTE_CHARS:
                result = "너무 짧음"
            elif haystack is None:
                result = "원문 없음"
            else:
                result = "일치" if normalize(quote) in haystack else "불일치"
            rows.append([case["id"], str(n), result, case.get("evidence", ""), quote[:40]])
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cases", type=Path)
    parser.add_argument("--sample", type=int, default=0, help="스크린샷 판독 사례 중 직접 대조할 수를 골라 출력")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if args.sample:
        pool = sorted(c["id"] for c in cases if c.get("evidence") == CAPTURE_EVIDENCE)
        picked = random.Random(args.seed).sample(pool, min(args.sample, len(pool)))
        print("직접 대조할 사례(캡처 이미지와 판독본을 나란히 본다):", ", ".join(picked) or "없음")
        return 0

    rows = verify(cases, args.cases.parent)
    out = args.cases.parent / f"verify_{args.cases.stem}.tsv"
    write_tsv(out, ["id", "quote", "result", "evidence", "head"], rows)
    bad = [r for r in rows if r[2] != "일치"]
    print(f"인용 {len(rows)}개 중 일치 {len(rows) - len(bad)}개 → {out}")
    for r in bad:
        print(f"  {r[0]} #{r[1]} {r[2]}: {r[4]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
