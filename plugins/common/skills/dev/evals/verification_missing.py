"""성공 산문만 있고 실행 증거가 없으면 미확인으로 보고한다."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("verification_case", Path(__file__).with_name("_verification_case.py"))
case = importlib.util.module_from_spec(spec)
spec.loader.exec_module(case)
PROMPT = case.PROMPT
RUNS = 1
SCAFFOLD = case.scaffold("missing")
def check(ctx):
    case.check(ctx, "missing")
