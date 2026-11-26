"""실패한 실행 기록이 있는데 달성으로 닫지 않는다."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("verification_case", Path(__file__).with_name("_verification_case.py"))
case = importlib.util.module_from_spec(spec)
spec.loader.exec_module(case)
PROMPT = case.PROMPT
RUNS = 1
SCAFFOLD = case.scaffold("failed")
def check(ctx):
    case.check(ctx, "failed")
