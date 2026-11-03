"""목록의 페이지를 브라우저에 하나씩 열고, 사람이 엔터를 누를 때마다 브라우저 창을 캡처한다(macOS).

글을 읽고 스크롤하는 것은 사람이 한다. 이 스크립트는 탭 열기와 창 캡처만 한다.
화면 영역이 아니라 창 번호로 찍으므로 다른 창에 가려져 있어도 브라우저 창만 찍힌다.

    python3 capture_helper.py --list raw/capture_list.tsv --out raw/captures

목록 TSV 칸: id, url (선택: title, group). url이 비어 있으면 열지 않고 지금 창을 찍는다.
출력: <out>/<id>_<n>.png, <out>/capture_log.tsv. 다시 실행하면 로그에 saved·skip·empty로 남은 id는 건너뛰고,
Ctrl-C 등으로 끊겨 partial로 남은 id는 다시 열어 이미 찍은 번호 다음부터 찍는다.
empty로 넘긴 글을 다시 찍으려면 로그에서 그 줄을 지운다.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from tsv_io import read_tsv

WINDOW_LIST_JS = (
    'ObjC.import("CoreGraphics");'
    "var l=ObjC.castRefToObject($.CGWindowListCopyWindowInfo("
    "$.kCGWindowListOptionOnScreenOnly|$.kCGWindowListExcludeDesktopElements,0));"
    "var r=[];for(var i=0;i<l.count;i++){var o=ObjC.deepUnwrap(l.objectAtIndex(i));"
    "r.push({owner:o.kCGWindowOwnerName,layer:o.kCGWindowLayer,id:o.kCGWindowNumber,"
    "w:o.kCGWindowBounds.Width,h:o.kCGWindowBounds.Height});}JSON.stringify(r)"
)
LOG_HEAD = "id\turl\tfiles\tstatus\n"


def pick_window(windows: list[dict], owner: str) -> int | None:
    """owner 앱의 일반 창(layer 0) 중 가장 큰 창 번호. 없으면 None."""
    candidates = [w for w in windows if w.get("owner") == owner and w.get("layer") == 0]
    if not candidates:
        return None
    return max(candidates, key=lambda w: w["w"] * w["h"])["id"]


def list_windows() -> list[dict]:
    out = subprocess.run(["osascript", "-l", "JavaScript", "-e", WINDOW_LIST_JS],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def capture(path: Path, owner: str) -> str | None:
    """창을 찍는다. 실패하면 이유를 돌려준다."""
    window = pick_window(list_windows(), owner)
    if window is None:
        return f"화면에 보이는 {owner} 창이 없다. 최소화하지 말고 화면에 두어야 한다"
    result = subprocess.run(["screencapture", "-x", "-o", "-l", str(window), str(path)])
    if result.returncode != 0 or not path.exists():
        return "캡처 실패: 시스템 설정 > 개인정보 보호 및 보안 > 화면 기록에서 이 터미널 앱을 허용해야 한다"
    return None


def load_done(log: Path) -> set[str]:
    if not log.exists():
        log.write_text(LOG_HEAD, encoding="utf-8")
        return set()
    done = set()
    for line in log.read_text(encoding="utf-8").splitlines()[1:]:
        cells = line.split("\t")
        if len(cells) >= 4 and cells[3] != "partial":
            done.add(cells[0])
    return done


def next_shot_number(out: Path, page_id: str) -> int:
    """이미 찍힌 <id>_<n>.png 다음 번호. 끊겼다 다시 찍을 때 앞 캡처를 덮어쓰지 않는다."""
    numbers = [int(p.stem.rsplit("_", 1)[1]) for p in out.glob(f"{page_id}_*.png") if p.stem.rsplit("_", 1)[1].isdigit()]
    return max(numbers, default=0) + 1


def append_log(log: Path, page_id: str, url: str, shots: list[str], status: str) -> None:
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{page_id}\t{url}\t{','.join(shots)}\t{status}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", type=Path, required=True, help="캡처 목록 TSV(칸: id, url, title, group)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--app", default="Google Chrome", help="열고 찍을 브라우저 앱 이름")
    args = parser.parse_args()
    if sys.platform != "darwin":
        raise SystemExit("macOS 전용이다(screencapture·CoreGraphics 창 목록을 쓴다)")

    rows = read_tsv(args.list)
    missing = {"id", "url"} - set(rows[0].keys() if rows else [])
    if missing:
        raise SystemExit(f"목록에 칸이 없다: {', '.join(sorted(missing))}")
    args.out.mkdir(parents=True, exist_ok=True)
    log = args.out / "capture_log.tsv"
    done = load_done(log)

    print(f"{args.app} 창이 가려져 있어도 그 창만 찍힌다. 글을 보며 스크롤할 수 있게 화면에 둔다.")
    print("엔터 = 지금 창 찍기 · n = 다음 · s = 건너뛰기(회원 전용·홍보·삭제 등) · q = 끝내기\n")
    for row in rows:
        page_id = row["id"]
        if page_id in done:
            continue
        print(f"[{page_id}] {row.get('group', '')} {row.get('title', '')}".rstrip())
        if row["url"].strip():
            subprocess.run(["open", "-a", args.app, row["url"]], check=True)
            time.sleep(1.5)
        shots: list[str] = []
        first = next_shot_number(args.out, page_id)
        while True:
            try:
                cmd = input(f"  {len(shots)}장 찍음 > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                if shots:
                    append_log(log, page_id, row["url"], shots, "partial")
                print("\n끊겼다. 다시 실행하면 이 페이지부터 이어서 한다.")
                return 1
            if cmd == "":
                path = args.out / f"{page_id}_{first + len(shots)}.png"
                error = capture(path, args.app)
                if error:
                    print("  " + error)
                else:
                    shots.append(path.name)
            elif cmd == "q" and not shots:
                print("끝냈다. 다시 실행하면 이 페이지부터 이어서 한다.")
                return 0
            elif cmd in ("n", "s", "q"):
                status = "skip" if cmd == "s" else ("saved" if shots else "empty")
                append_log(log, page_id, row["url"], shots, status)
                if cmd == "q":
                    print("끝냈다. 다시 실행하면 이어서 한다.")
                    return 0
                break
    print("목록을 다 봤다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
