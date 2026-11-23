"""GRADER="llm" 케이스의 run을 스킬 루브릭(references/review-rubric.md)으로 채점한다.

채점자는 도구 없이 사용자 요청 원문·루브릭·산출물만 받는다. 결과는 판정의 근거로만 쓰고,
케이스를 FAIL로 만들지 않는다(_verdict.judge의 `결정:` 참조).
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from _harness import GRADER_RUBRIC, RunCost, RunResult, cost_from_events, run_claude

RUBRIC_PATH = Path(GRADER_RUBRIC)

# 결정: 산출물은 프롬프트 인자로 넘기므로 합계를 글자 수로 자른다. Linux는 인자 하나가 128KB를 넘으면
#   실행 자체가 실패하고(한글 1자 = 3바이트), 생성 문서는 보통 수천 자라 이 상한에 잘 닿지 않는다.
#   잘렸으면 채점자에게 그렇다고 알린다.
MAX_ARTIFACT_CHARS = 30_000


@dataclass
class GradeItem:
    no: int
    passed: bool
    quote: str = ""
    fix: str = ""


@dataclass
class Grade:
    items: list[GradeItem] = field(default_factory=list)
    error: str = ""            # 비어 있지 않으면 채점 실패(사유)
    cost: RunCost | None = None

    @property
    def passed_all(self) -> bool:
        return not self.error and all(i.passed for i in self.items)

    @property
    def failed_nos(self) -> list[int]:
        return [i.no for i in self.items if not i.passed]

    def to_json(self) -> dict:
        return {"passed_all": self.passed_all, "error": self.error,
                "items": [asdict(i) for i in self.items],
                "cost": None if self.cost is None else asdict(self.cost)}


def rubric_item_numbers(rubric: str) -> list[int]:
    """루브릭 표의 `| <번호> | ...` 행 번호."""
    return [int(n) for n in re.findall(r"(?m)^\|\s*(\d+)\s*\|", rubric)]


def parse_grade(text: str, expected: list[int]) -> tuple[list[GradeItem], str]:
    """채점자 응답에서 항목을 읽는다. 돌려주는 두 번째 값이 비어 있지 않으면 그 사유로 실패다."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return [], "JSON 없음"
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        return [], f"JSON 파싱: {e.msg}"
    raw = data.get("items") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return [], "items 목록 없음"
    items: list[GradeItem] = []
    for r in raw:
        if not isinstance(r, dict) or not isinstance(r.get("no"), int) or not isinstance(r.get("passed"), bool):
            return [], f"항목 형식 오류: {str(r)[:80]}"
        items.append(GradeItem(r["no"], r["passed"], str(r.get("quote", "")), str(r.get("fix", ""))))
    got = [i.no for i in items]
    missing = sorted(set(expected) - set(got))
    extra = sorted(set(got) - set(expected))
    if missing or extra or len(got) != len(set(got)):
        return [], f"항목 불일치: 누락 {missing} · 없는 번호 {extra}"
    return sorted(items, key=lambda i: i.no), ""


def collect_artifacts(run: RunResult) -> str:
    """run이 새로 만들거나 바꾼 텍스트 파일과 마지막 응답을 한 덩어리로 만든다."""
    parts: list[str] = []
    if run.workdir is not None:
        for rel in run.changed_files():
            data = (run.workdir / rel).read_bytes()
            if b"\x00" in data:
                continue
            parts.append(f"=== 파일: {rel}\n{data.decode('utf-8', errors='replace')}")
    parts.append(f"=== 마지막 응답\n{run.final_text}")
    text = "\n\n".join(parts)
    if len(text) > MAX_ARTIFACT_CHARS:
        text = text[:MAX_ARTIFACT_CHARS] + f"\n\n(산출물이 길어 {MAX_ARTIFACT_CHARS}자에서 잘랐다)"
    return text


def grading_prompt(request: str, rubric: str, artifacts: str) -> str:
    return (
        "너는 이 작업의 맥락을 모르는 검수자다. 아래 사용자 요청 원문, 검수 기준, 산출물만 보고 "
        "검수 기준의 항목마다 통과·미통과를 정한다. 산출물에서 인용할 문장이 없으면 통과로 보지 않는다.\n"
        "답은 다른 말 없이 JSON 하나만 쓴다:\n"
        '{"items": [{"no": 1, "passed": true, "quote": "산출물에서 인용한 문장", "fix": "미통과일 때 고칠 문장"}]}\n\n'
        f"## 사용자 요청 원문\n{request}\n\n## 검수 기준\n{rubric}\n\n## 산출물\n{artifacts}\n"
    )


def grade_run(run: RunResult, *, skill_dir: Path, request: str, model: str, timeout: int,
              runner=run_claude) -> Grade:
    """구조 검사를 통과한 run 하나를 채점한다. 어떤 실패도 예외가 아니라 Grade.error로 돌려준다."""
    rubric_file = skill_dir / RUBRIC_PATH
    if not rubric_file.is_file():
        return Grade(error=f"루브릭 없음: {RUBRIC_PATH.as_posix()}")
    try:
        rubric = rubric_file.read_text(encoding="utf-8")
    except UnicodeError as e:
        return Grade(error=f"루브릭을 읽지 못함: {e}")
    expected = rubric_item_numbers(rubric)
    if not expected:
        return Grade(error="루브릭에 번호 붙은 항목 행이 없다")

    prompt = grading_prompt(request, rubric, collect_artifacts(run))
    with tempfile.TemporaryDirectory(prefix="buildskill-grade-") as cwd:
        try:
            events = runner(
                prompt, Path(cwd),
                # 빈 cwd + project 설정만 → 레포·사용자 지침을 읽지 않는다. 도구는 모두 끈다
                extra_args=["--setting-sources", "project", "--strict-mcp-config", "--tools", ""],
                permission_mode="default", model=model, max_turns=2, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return Grade(error=f"시간 초과 {timeout}초")
        except (RuntimeError, OSError) as e:   # OSError: claude 없음, 인자 길이 초과(E2BIG) 등
            return Grade(error=f"호출 실패: {str(e)[:200]}")

    cost = cost_from_events(events)
    if any(e.get("type") == "result" and e.get("is_error") for e in events):
        return Grade(error="채점 호출이 오류로 끝남", cost=cost)
    texts = [c.get("text", "") for e in events if e.get("type") == "assistant"
             for c in e.get("message", {}).get("content", [])
             if isinstance(c, dict) and c.get("type") == "text"]
    items, error = parse_grade(texts[-1] if texts else "", expected)
    return Grade(items=items, error=error, cost=cost)


def summarize(grades: list[Grade | None]) -> str:
    """케이스 하나의 채점 요약 한 줄. None은 구조 검사에서 떨어져 채점하지 않은 run이다."""
    done = [g for g in grades if g is not None]
    if not done:
        return "LLM 채점 대상 run 없음"
    ok = [g for g in done if not g.error]
    line = f"LLM {sum(g.passed_all for g in ok)}/{len(ok)} 통과"
    failed: dict[int, int] = {}
    for g in ok:
        for no in g.failed_nos:
            failed[no] = failed.get(no, 0) + 1
    if failed:
        line += "(미통과 " + ", ".join(f"#{no}×{n}" for no, n in sorted(failed.items())) + ")"
    errors = [g for g in done if g.error]
    if errors:
        line += f" · 채점 실패 {len(errors)}: {errors[0].error}"
    return line
