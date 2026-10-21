"""통과 뒤 코드가 바뀐 기록을 최종 코드의 증거로 인정하지 않는다."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("verification_case", Path(__file__).with_name("_verification_case.py"))
case = importlib.util.module_from_spec(spec)
spec.loader.exec_module(case)
PROMPT = case.PROMPT
RUNS = 1
SCAFFOLD = case.scaffold("stale")
def check(ctx):
    case.check(ctx, "stale")
