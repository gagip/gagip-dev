"""실제 PNG 바이트와 가짜 adb 실행기로 흰 화면·치명 오류·워치 판정을 확인한다."""
from datetime import datetime
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

import prove_android_launch as prove


def make_png(width, height, pixel, color_type=6):
    """pixel(x, y) -> 채널 튜플. 필터 0(없음) PNG를 만든다."""
    channels = {2: 3, 6: 4}[color_type]
    raw = b"".join(
        b"\x00" + bytes(c for x in range(width) for c in pixel(x, y)[:channels]) for y in range(height)
    )

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    header = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)


def text_on_white(x, y):
    return BLACK if 20 <= x < 80 and 30 <= y < 170 and (x + y) % 2 == 0 else WHITE


class BlankJudgementTests(unittest.TestCase):
    def test_solid_white_fails(self):
        self.assertTrue(prove.is_blank(make_png(100, 200, lambda x, y: WHITE)))

    def test_white_with_status_bar_icons_still_fails(self):
        png = make_png(100, 200, lambda x, y: BLACK if y < 8 and x % 3 == 0 else WHITE)
        self.assertTrue(prove.is_blank(png))

    def test_white_background_with_text_passes(self):
        self.assertFalse(prove.is_blank(make_png(100, 200, text_on_white)))

    def test_rgb_png_is_read(self):
        self.assertTrue(prove.is_blank(make_png(10, 20, lambda x, y: (255, 255, 255), color_type=2)))

    def test_non_png_is_rejected(self):
        with self.assertRaises(ValueError):
            prove.same_color_ratio(b"not a png")


class DeviceTests(unittest.TestCase):
    def test_watch_characteristics(self):
        self.assertTrue(prove.is_watch("nosdcard,watch"))

    def test_phone_characteristics(self):
        self.assertFalse(prove.is_watch("nosdcard,phone"))


PKG = "com.example.app"
CRASH = f"""11-05 10:00:00.000  4321  4321 E AndroidRuntime: FATAL EXCEPTION: main
11-05 10:00:00.000  4321  4321 E AndroidRuntime: Process: {PKG}, PID: 4321
11-05 10:00:00.000  4321  4321 E AndroidRuntime: java.lang.RuntimeException: boom
"""


class FatalErrorTests(unittest.TestCase):
    def test_same_package_is_found(self):
        self.assertEqual(len(prove.fatal_errors(CRASH, PKG)), 1)

    def test_other_package_is_ignored(self):
        self.assertEqual(prove.fatal_errors(CRASH, "com.other.app"), [])

    def test_prefix_package_is_not_confused(self):
        self.assertEqual(prove.fatal_errors(CRASH, PKG + "x"), [])

    def test_same_pid_is_found(self):
        log = "11-05 10:00:00.000  777  777 E AndroidRuntime: FATAL EXCEPTION: main\n"
        self.assertEqual(len(prove.fatal_errors(log, PKG, pid="777")), 1)

    def test_non_fatal_runtime_line_is_ignored(self):
        self.assertEqual(prove.fatal_errors("11-05 10:00:00.000  1  1 D AndroidRuntime: Shutting down VM\n", PKG), [])


class FakeAdb:
    def __init__(self, characteristics="nosdcard,phone", png=b"", pid=b"4321\n", log="", launch_out=b"Events injected: 1\n"):
        self.calls = []
        self.characteristics, self.png, self.pid, self.log, self.launch_out = characteristics, png, pid, log, launch_out

    def __call__(self, args):
        self.calls.append(args)
        tail = args[3:]
        if tail[:2] == ["getprop", "ro.build.characteristics"] or tail[1:3] == ["getprop", "ro.build.characteristics"]:
            return 0, self.characteristics.encode()
        if "screencap" in args:
            return 0, self.png
        if "pidof" in args:
            return 0, self.pid
        if "-d" in args:
            return 0, self.log.encode()
        if "monkey" in args or "am" in args:
            return 0, self.launch_out
        return 0, b""


class ProveFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.shots = Path(self.tmp.name) / "shots"
        self.good = make_png(100, 200, text_on_white)

    def go(self, adb, activity=""):
        return prove.prove("emu", PKG, activity, self.shots, adb, sleep=lambda _: None,
                           now=lambda: datetime(2026, 11, 5, 10, 0, 0))

    def test_pass_saves_screenshot_and_clears_log_first(self):
        adb = FakeAdb(png=self.good)
        code, report = self.go(adb)
        self.assertEqual(code, prove.EXIT_PASS)
        self.assertEqual(Path(report["screenshot"]).read_bytes(), self.good)
        verbs = [c[3:5] for c in adb.calls]
        self.assertLess(verbs.index(["logcat", "-c"]), verbs.index(["shell", "monkey"]))

    def test_activity_uses_am_start(self):
        adb = FakeAdb(png=self.good)
        self.go(adb, activity=".Main")
        self.assertTrue(any(c[3:7] == ["shell", "am", "start", "-n"] for c in adb.calls))

    def test_watch_is_rejected_before_launch(self):
        adb = FakeAdb(characteristics="nosdcard,watch", png=self.good)
        code, _ = self.go(adb)
        self.assertEqual(code, prove.EXIT_WATCH)
        self.assertFalse(any("monkey" in c for c in adb.calls))

    def test_blank_screen_fails(self):
        code, report = self.go(FakeAdb(png=make_png(100, 200, lambda x, y: WHITE)))
        self.assertEqual(code, prove.EXIT_FAIL)
        self.assertFalse(report["checks"]["흰 화면 아님"])

    def test_fatal_exception_fails(self):
        code, report = self.go(FakeAdb(png=self.good, log=CRASH))
        self.assertEqual(code, prove.EXIT_FAIL)
        self.assertFalse(report["checks"]["치명 오류 없음"])

    def test_dead_process_fails(self):
        code, _ = self.go(FakeAdb(png=self.good, pid=b""))
        self.assertEqual(code, prove.EXIT_FAIL)

    def test_launch_error_fails(self):
        code, _ = self.go(FakeAdb(png=self.good, launch_out=b"** No activities found to run, monkey aborted.\n"))
        self.assertEqual(code, prove.EXIT_FAIL)

    def test_broken_screenshot_fails(self):
        code, report = self.go(FakeAdb(png=b"garbage"))
        self.assertEqual(code, prove.EXIT_FAIL)
        self.assertIn("image_error", report)


if __name__ == "__main__":
    unittest.main()
