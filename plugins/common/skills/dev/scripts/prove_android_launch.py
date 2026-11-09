#!/usr/bin/env python3
"""안드로이드 기기에서 앱을 실행해 치명 오류·프로세스 종료·흰 화면이 없는지 증거(캡처)와 함께 판정한다.

    python3 prove_android_launch.py --serial <adb 기기> --package <앱 패키지> [--activity <액티비티>] --shots <폴더>

종료 코드: 통과 0, 실패 1, 워치 기기 거부 2.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import zlib
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Callable

WAIT_SECONDS = 8
# 상태 표시줄·내비게이션 막대는 앱이 아니라 OS가 그려서 빈 앱 화면에도 시계·아이콘 픽셀이 섞인다.
TOP_CROP = 0.05
BOTTOM_CROP = 0.08
# 99%: 정상 화면이 한 색으로 99%를 덮는 일은 없고, 빈 화면은 가장자리 잡음 정도만 남는다.
SAME_COLOR_FAIL_RATIO = 0.99

EXIT_PASS, EXIT_FAIL, EXIT_WATCH = 0, 1, 2

# (인자 목록) -> (종료 코드, stdout 바이트)
Runner = Callable[[list[str]], tuple[int, bytes]]


def is_watch(characteristics: str) -> bool:
    return "watch" in characteristics.lower()


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def decode_png(data: bytes) -> tuple[int, int, int, list[bytes]]:
    """8비트 회색·RGB·회색+알파·RGBA, 비인터레이스 PNG를 (너비, 높이, 픽셀 바이트 수, 행 목록)으로 푼다."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("PNG 서명이 아니다")
    pos, idat, header = 8, [], None
    while pos + 8 <= len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            header = body
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    if header is None or not idat:
        raise ValueError("IHDR 또는 IDAT가 없다")
    width, height = int.from_bytes(header[:4], "big"), int.from_bytes(header[4:8], "big")
    depth, color, interlace = header[8], header[9], header[12]
    channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(color)
    if depth != 8 or channels is None or interlace:
        raise ValueError(f"지원하지 않는 PNG(깊이 {depth}, 색 유형 {color}, 인터레이스 {interlace})")
    raw = zlib.decompress(b"".join(idat))
    stride = width * channels
    if len(raw) != height * (stride + 1):
        raise ValueError("PNG 데이터 길이가 헤더와 맞지 않는다")
    rows: list[bytes] = []
    prev = bytearray(stride)
    for y in range(height):
        start = y * (stride + 1)
        ft = raw[start]
        cur = bytearray(raw[start + 1:start + 1 + stride])
        if ft == 1:
            for i in range(channels, stride):
                cur[i] = (cur[i] + cur[i - channels]) & 255
        elif ft == 2:
            for i in range(stride):
                cur[i] = (cur[i] + prev[i]) & 255
        elif ft == 3:
            for i in range(stride):
                left = cur[i - channels] if i >= channels else 0
                cur[i] = (cur[i] + ((left + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                left = cur[i - channels] if i >= channels else 0
                upleft = prev[i - channels] if i >= channels else 0
                cur[i] = (cur[i] + _paeth(left, prev[i], upleft)) & 255
        elif ft != 0:
            raise ValueError(f"알 수 없는 PNG 필터 {ft}")
        rows.append(bytes(cur))
        prev = cur
    return width, height, channels, rows


def same_color_ratio(png: bytes, top: float = TOP_CROP, bottom: float = BOTTOM_CROP) -> float:
    """시스템 막대 영역을 뺀 픽셀 중 가장 많은 한 색의 비율."""
    _, height, channels, rows = decode_png(png)
    body = rows[int(height * top):height - int(height * bottom)]
    if not body:
        raise ValueError("판정할 픽셀 영역이 없다")
    counts: Counter[bytes] = Counter()
    for row in body:
        counts.update(row[i:i + channels] for i in range(0, len(row), channels))
    return counts.most_common(1)[0][1] / sum(counts.values())


def is_blank(png: bytes) -> bool:
    return same_color_ratio(png) >= SAME_COLOR_FAIL_RATIO


_LOG_PID = re.compile(r"^\S+\s+\S+\s+(\d+)\s+\d+\s+[A-Z]\s")


def fatal_errors(log: str, package: str, pid: str = "") -> list[str]:
    """logcat 덤프에서 해당 패키지(또는 PID)의 FATAL EXCEPTION 줄을 돌려준다."""
    lines = log.splitlines()
    found = []
    for index, line in enumerate(lines):
        if "FATAL EXCEPTION" not in line or "AndroidRuntime" not in line:
            continue
        match = _LOG_PID.match(line)
        same_pid = bool(pid and match and match.group(1) == pid)
        named = any(re.search(rf"Process: {re.escape(package)}(,|\s|$)", nxt) for nxt in lines[index + 1:index + 6])
        if same_pid or named:
            found.append(line.strip())
    return found


_LAUNCH_ERRORS = ("Error", "does not exist", "No activities found", "Aborted")


def prove(serial: str, package: str, activity: str, shots: Path, run: Runner,
          sleep: Callable[[float], None] = time.sleep, now: Callable[[], datetime] = datetime.now) -> tuple[int, dict]:
    adb = ["adb", "-s", serial]
    report: dict = {"serial": serial, "package": package, "checks": {}, "screenshot": None}

    code, out = run([*adb, "shell", "getprop", "ro.build.characteristics"])
    characteristics = out.decode(errors="replace").strip()
    report["characteristics"] = characteristics
    if code != 0:
        report["error"] = "기기 종류를 읽지 못했다"
        return EXIT_FAIL, report
    if is_watch(characteristics):
        report["error"] = "워치 기기는 이 스크립트가 지원하지 않는다"
        return EXIT_WATCH, report

    run([*adb, "logcat", "-c"])
    if activity:
        launch = [*adb, "shell", "am", "start", "-n", f"{package}/{activity}"]
    else:
        launch = [*adb, "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"]
    code, out = run(launch)
    text = out.decode(errors="replace")
    report["launch_output"] = text.strip()
    if code != 0 or any(word in text for word in _LAUNCH_ERRORS):
        report["error"] = "앱 실행 명령이 실패했다"
        return EXIT_FAIL, report

    sleep(WAIT_SECONDS)

    code, png = run([*adb, "exec-out", "screencap", "-p"])
    shots.mkdir(parents=True, exist_ok=True)
    path = shots / f"{now():%Y%m%d-%H%M%S}_{package}.png"
    path.write_bytes(png)
    report["screenshot"] = str(path)

    _, pid_out = run([*adb, "shell", "pidof", package])
    pid = pid_out.decode(errors="replace").strip().split(" ")[0]
    report["pid"] = pid
    _, log_out = run([*adb, "logcat", "-d"])
    fatals = fatal_errors(log_out.decode(errors="replace"), package, pid)
    report["fatal"] = fatals

    report["checks"]["프로세스 실행 중"] = bool(pid)
    report["checks"]["치명 오류 없음"] = not fatals
    try:
        ratio = same_color_ratio(png) if code == 0 else None
        report["same_color_ratio"] = ratio
        report["checks"]["흰 화면 아님"] = ratio is not None and ratio < SAME_COLOR_FAIL_RATIO
    except (ValueError, zlib.error) as error:
        report["checks"]["흰 화면 아님"] = False
        report["image_error"] = str(error)
    return (EXIT_PASS if all(report["checks"].values()) else EXIT_FAIL), report


def adb_runner(args: list[str]) -> tuple[int, bytes]:
    done = subprocess.run(args, capture_output=True, timeout=60)
    return done.returncode, done.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--serial", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--activity", default="")
    parser.add_argument("--shots", required=True, type=Path)
    args = parser.parse_args(argv)
    code, report = prove(args.serial, args.package, args.activity, args.shots, adb_runner)
    for name, ok in report["checks"].items():
        print(f"{'통과' if ok else '실패'}: {name}")
    for key in ("error", "same_color_ratio", "screenshot", "image_error"):
        if report.get(key) is not None:
            print(f"{key}: {report[key]}")
    for line in report.get("fatal", []):
        print(f"치명 오류: {line}")
    print("결과:", {EXIT_PASS: "통과", EXIT_FAIL: "실패", EXIT_WATCH: "워치 거부"}[code])
    return code


if __name__ == "__main__":
    sys.exit(main())
