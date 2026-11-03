"""이 스킬 스크립트들이 같이 쓰는 TSV 읽기·쓰기와 요청 UA."""
import csv
from pathlib import Path

UA = "market-research-skill/1.0 (manual research; low rate)"


def read_tsv(path: Path) -> list[dict]:
    """따옴표를 특별 취급하지 않고 읽는다. 제목이 따옴표로 시작해도 행이 합쳐지지 않는다. 엑셀 BOM도 받는다."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


def write_tsv(path: Path, head: list[str], rows: list[list[str]]) -> None:
    def cell(value: str) -> str:
        return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")
    lines = ["\t".join(head)] + ["\t".join(cell(c) for c in r) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
