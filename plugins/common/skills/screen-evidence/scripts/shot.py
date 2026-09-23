#!/usr/bin/env python3
"""브라우저 창 영역을 캡처하고 상단 브라우저 알림 영역을 잘라낸다 (macOS).

창 좌표는 자동으로 못 구한다 — 어느 창을 찍을지는 사람이 정할 문제다. 찍을 창의 좌표는
AppleScript로 조회해 넘긴다:

    osascript -e 'tell application "Google Chrome" to get bounds of window 1'

사용:
    python3 shot.py <출력경로> --region X,Y,W,H [--strip-top 58] [--focus-away]

--focus-away 는 캡처 직전 다른 창을 앞으로 보낸다. 브라우저 자동화 확장은 제어 중인 탭이
화면 포커스를 가진 동안에만 가장자리 표시를 그리므로, 포커스를 옮기면 표시 없이 찍힌다.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def focus_other_window() -> None:
    """브라우저의 다른 창을 앞으로 보내 캡처 대상 탭에서 포커스를 뺀다."""
    script = (
        'tell application "Google Chrome"\n'
        "  if (count of windows) > 1 then set index of window 2 to 1\n"
        "  activate\n"
        "end tell"
    )
    subprocess.run(["osascript", "-e", script], capture_output=True)


def strip_top(path: Path, pixels: int) -> tuple[int, int]:
    from PIL import Image

    im = Image.open(path).convert("RGB")
    w, h = im.size
    im.crop((0, pixels, w, h)).save(path)
    return Image.open(path).size


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output", type=Path)
    ap.add_argument(
        "--region",
        required=True,
        help="캡처할 화면 영역 X,Y,W,H (화면 좌표, 포인트 단위)",
    )
    ap.add_argument(
        "--strip-top",
        type=int,
        default=58,
        help="캡처 후 잘라낼 상단 픽셀 수. 브라우저 자동화 알림 배너 높이. 0이면 자르지 않는다",
    )
    ap.add_argument(
        "--focus-away",
        action="store_true",
        help="캡처 직전 다른 창을 앞으로 보내 가장자리 표시가 안 그려지게 한다",
    )
    args = ap.parse_args()

    if sys.platform != "darwin":
        print("이 스크립트는 macOS 전용이다. 다른 환경에서는 그 환경의 화면 캡처 명령을 쓴다.")
        return 1

    try:
        x, y, w, h = (int(v) for v in args.region.split(","))
    except ValueError:
        print("--region 은 X,Y,W,H 형식이어야 한다 (예: 1512,122,1920,958)")
        return 1

    if args.focus_away:
        focus_other_window()
        subprocess.run(["sleep", "2"])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    run(["screencapture", "-x", f"-R{x},{y},{w},{h}", str(args.output)])

    size = (w, h)
    if args.strip_top > 0:
        size = strip_top(args.output, args.strip_top)

    print(f"{args.output.name} {size[0]}x{size[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
