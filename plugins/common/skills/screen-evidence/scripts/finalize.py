#!/usr/bin/env python3
"""캡처 폴더의 자동화 표시를 재서 잘라내고, 규격을 통일하고, 확인용 격자를 만든다.

브라우저 자동화 확장은 제어 중인 화면 가장자리에 색 띠를 그린다. 그 띠는 안쪽으로 서서히
옅어지므로 눈대중으로 자르면 너무 많이(내용 손실) 또는 너무 적게(잔재) 자르게 된다. 이
스크립트는 각 변에서 색 편차가 사라지는 지점을 실제로 스캔해 필요한 최소 폭을 구한다.

사용:
    python3 finalize.py <폴더> [--margin N] [--dry-run] [--no-grid]

--margin 을 주면 측정을 건너뛰고 그 값으로 자른다. 주지 않으면 측정값에 여유를 더해 정한다.
크롭은 폴더 전체에 같은 값으로 적용한다 — 장마다 크기가 다르면 제출물이 정돈되지 않아 보인다.
"""

import argparse
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("Pillow가 필요하다: pip install Pillow")

# 색 띠 판정 기준. 무채색 UI에서 빨강 성분이 파랑보다 이만큼 높으면 띠로 본다.
TINT_THRESHOLD = 4
# 측정값에 더할 여유. 띠 끝이 완만해 측정 지점보다 조금 더 번져 있는 경우를 흡수한다.
MARGIN_PADDING = 3
# 한 변에서 탐색할 최대 깊이. 이보다 깊으면 띠가 아니라 실제 UI다.
MAX_SCAN = 80


def tint(px: tuple[int, int, int]) -> int:
    r, _, b = px
    return r - b


def scan_depth(im: Image.Image) -> int:
    """네 변에서 색 띠가 몇 픽셀까지 번졌는지 잰다. 각 변의 중앙 선을 따라 안쪽으로 훑는다."""
    px = im.load()
    w, h = im.size
    mid_y, mid_x = h // 2, w // 2
    depths = []

    for probe in (
        lambda i: px[i, mid_y],  # 왼쪽
        lambda i: px[w - 1 - i, mid_y],  # 오른쪽
        lambda i: px[mid_x, i],  # 위
        lambda i: px[mid_x, h - 1 - i],  # 아래
    ):
        depth = 0
        for i in range(min(MAX_SCAN, w // 2, h // 2)):
            if tint(probe(i)) <= TINT_THRESHOLD:
                depth = i
                break
            depth = i + 1
        depths.append(depth)

    return max(depths)


def residual(im: Image.Image) -> int:
    """자른 뒤 가장자리에 남은 최대 색 편차. 좌·우·아래만 본다 — 위쪽 가장자리에는
    알림 배지 같은 실제 붉은 UI가 걸리는 일이 흔해 오탐이 난다."""
    px = im.load()
    w, h = im.size
    worst = 0
    for y in range(h):
        for x in (0, 1, 2, w - 3, w - 2, w - 1):
            worst = max(worst, tint(px[x, y]))
    for x in range(w):
        for y in (h - 3, h - 2, h - 1):
            worst = max(worst, tint(px[x, y]))
    return worst


def build_grid(paths: list[Path], out: Path, thumb_width: int = 600) -> None:
    thumbs = []
    for p in paths:
        im = Image.open(p)
        w, h = im.size
        thumbs.append(im.resize((thumb_width, int(h * thumb_width / w))))
    tw, th = thumbs[0].size
    cols = 3 if len(thumbs) > 4 else max(1, len(thumbs))
    rows = (len(thumbs) + cols - 1) // cols
    grid = Image.new("RGB", (tw * cols, th * rows), "#cccccc")
    for i, im in enumerate(thumbs):
        grid.paste(im, ((i % cols) * tw, (i // cols) * th))
    grid.save(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--margin", type=int, help="측정을 건너뛰고 이 폭으로 자른다")
    ap.add_argument("--dry-run", action="store_true", help="측정만 하고 자르지 않는다")
    ap.add_argument("--no-grid", action="store_true", help="확인용 격자를 만들지 않는다")
    args = ap.parse_args()

    paths = sorted(args.folder.glob("*.png"))
    if not paths:
        print(f"{args.folder}에 png가 없다")
        return 1

    images = {p: Image.open(p).convert("RGB") for p in paths}

    sizes = {im.size for im in images.values()}
    if len(sizes) > 1:
        print(f"경고: 크기가 섞여 있다 {sizes} — 같은 창에서 찍었는지 확인하라")

    measured = {p: scan_depth(im) for p, im in images.items()}
    for p in paths:
        print(f"  {p.name}  색 띠 {measured[p]}px")

    margin = args.margin if args.margin is not None else max(measured.values()) + MARGIN_PADDING
    print(f"\n크롭 폭: {margin}px (전량 동일)")

    if args.dry_run:
        return 0

    for p, im in images.items():
        w, h = im.size
        cropped = im.crop((margin, margin, w - margin, h - margin))
        cropped.save(p)
        left = residual(cropped)
        flag = "" if left <= TINT_THRESHOLD else "  ← 잔재 남음, 다시 찍을 것"
        print(f"  {p.name}  {cropped.size[0]}x{cropped.size[1]}  잔재 {left}{flag}")

    if not args.no_grid:
        grid_path = args.folder / "_확인용격자.png"
        build_grid(paths, grid_path)
        print(f"\n확인용 격자: {grid_path}")
        print("수치 검사는 실제 UI의 붉은 요소도 잡는다 — 이 격자를 눈으로 확인하라")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
