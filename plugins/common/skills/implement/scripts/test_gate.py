"""단계 관문이 실제로 거부·통과를 가르는지 확인한다.

관문은 "코드가 판정한다"는 조직 규약을 떠받치는 유일한 부품이다. 그 부품이
통과만 시키면 규약은 이름만 남는다. 그래서 여기서는 단계마다 **정상 픽스처가
통과하는지**와 **결함을 하나 주입하면 실패하는지**를 짝으로 확인한다.

git을 실제로 돌리는 관문(branch·implement·ship·close)은 임시 저장소를 만들어 검사한다 —
저장소 없이 마크다운만 놓고 검사하면 정작 그 관문이 보는 것을 안 보게 된다.
나머지 단계는 저장소를 만들지 않는다(케이스마다 8개 프로세스를 띄우던 것을 없앴다).

실행: python3 test_gate.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import fixtures  # noqa: E402
import gate  # noqa: E402
import handoff  # noqa: E402

BRANCH = "feat/12-add-thing"

# 저장소를 실제로 들여다보는 단계. 나머지 케이스는 만들지 않는다.
GIT_STAGES = frozenset({"branch", "implement", "ship", "close"})

INTAKE_GOOD = """# intake

## 출처

이슈 #12 — 로그인 화면 에러 문구 누락

## 무엇을 고치나

| 파일 | 조치 |
|---|---|
| a.txt | 문구 추가 |

## 검증 조건

- `npm test` 통과
- 화면에 문구가 보이는지 사람 확인

## 범위 밖

- 서버 응답 형식 변경
"""

BRANCH_GOOD = f"""# branch

브랜치: `{BRANCH}`
작업 위치: 별도 워크트리
"""

IMPLEMENT_GOOD = """# implement

## 바꾼 것

- a.txt에 문구 추가
"""

SIMPLIFY_GOOD = """# simplify

## 정리 결과

없음 — 중복·미사용 코드가 나오지 않았다.
"""

REVIEW_GOOD = """# review

## 판정

| 등급 | 내용 | 반영 |
|---|---|---|
| 🔴 | 외부 입력 검증 없음 | 반영 |
| 🟡 | 변수명이 모호 | 미반영 |
"""

DOCS_GOOD = """# docs

## 문서 영향

문서 영향 없음.
"""

SHIP_GOOD = """# ship

PR: https://github.com/example-org/example-app/pull/123
"""

CLOSE_GOOD = """# close

## 종결

달성 — 검증 조건을 전부 확인했다.
"""

ARTIFACTS = {
    "intake": ("00_intake.md", INTAKE_GOOD),
    "branch": ("01_branch.md", BRANCH_GOOD),
    "implement": ("02_implement.md", IMPLEMENT_GOOD),
    "simplify": ("03_simplify.md", SIMPLIFY_GOOD),
    "review": ("04_review.md", REVIEW_GOOD),
    "docs": ("05_docs.md", DOCS_GOOD),
    "ship": ("07_ship.md", SHIP_GOOD),
    "close": ("08_close.md", CLOSE_GOOD),
}


def _run(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


def make_repo(root: Path, *, author: str | None = None,
              subject: str = "feat: 테스트 변경", dirty: bool = False,
              empty: bool = False) -> Path:
    """base(main) 위에 작업 브랜치를 만든 임시 저장소."""
    repo = root / "repo"
    repo.mkdir()
    _run(repo, "init", "-b", "main")
    _run(repo, "config", "user.email", "dev@example.com")
    _run(repo, "config", "user.name", "Dev")
    (repo / "a.txt").write_text("base\n", encoding="utf-8")
    _run(repo, "add", ".")
    _run(repo, "commit", "-m", "chore: 최초 커밋")
    _run(repo, "switch", "-c", BRANCH)

    if not empty:
        (repo / "a.txt").write_text("base\n문구\n", encoding="utf-8")
        _run(repo, "add", ".")
        args = ["commit", "-m", subject]
        if author:
            args = ["-c", f"user.email={author}", *args]
        _run(repo, *args)
    if dirty:
        (repo / "b.txt").write_text("작업 중\n", encoding="utf-8")
    return repo


def make_cycle(dest: Path, repo: Path | str, *,
               overrides: dict[str, str] | None = None,
               meta: dict[str, str] | None = None,
               stages: tuple[str, ...] = tuple(ARTIFACTS)) -> Path:
    """dest에 단계 산출물과 handoff.md를 깐다. overrides로 결함을 주입한다.

    회귀 채점기(evals/regression/*/check.py)도 이 함수로 픽스처를 만든다 —
    핸드오프 계약이 바뀌었을 때 고칠 자리를 하나로 둔다.
    """
    rows = {k: ("완료", ARTIFACTS[k][0]) for k in stages}
    fixtures.write_cycle(dest, {
        "cycle_id": "2026-08-27_테스트",
        "title": "관문 테스트",
        "status": "달성",
        "repo": str(repo),
        "branch": BRANCH,
        "base": "main",
        "allow_main": "true",  # 임시 저장소는 항상 메인 워크트리다
        **(meta or {}),
    }, rows)
    for key in stages:
        name, text = ARTIFACTS[key]
        (dest / name).write_text((overrides or {}).get(key, text), encoding="utf-8")
    return dest


def gate_of(cycle: Path, stage: str) -> list[str]:
    ok, fails = gate.check_stage(handoff.load(cycle), stage)
    return fails


CASES: list[tuple[str, str, str, dict]] = [
    # (이름, 단계, 기대, 픽스처 인자)
    ("intake: 정상", "intake", "통과", {}),
    ("intake: 검증 조건 절 삭제", "intake", "실패",
     {"overrides": {"intake": INTAKE_GOOD.replace("## 검증 조건", "## 확인")}}),
    ("intake: 검증 조건이 명령도 사람확인도 아님", "intake", "실패",
     {"overrides": {"intake": INTAKE_GOOD.replace("- `npm test` 통과", "- 잘 되는지 본다")
                    .replace("- 화면에 문구가 보이는지 사람 확인", "- 대충 확인")}}),

    ("branch: 정상", "branch", "통과", {}),
    ("branch: 브랜치명 형식 위반", "branch", "실패", {"meta": {"branch": "my-work"}}),
    ("branch: 메인 워크트리인데 allow_main이 false", "branch", "실패",
     {"meta": {"allow_main": "false"}}),

    ("implement: 정상", "implement", "통과", {}),
    ("implement: 바뀐 것이 없음", "implement", "실패", {"repo": {"empty": True}}),
    ("implement: base가 비어 있음", "implement", "실패", {"meta": {"base": ""}}),

    ("simplify: 정상", "simplify", "통과", {}),
    ("simplify: 정리 결과가 빔", "simplify", "실패",
     {"overrides": {"simplify": "# simplify\n\n## 정리 결과\n\n"}}),
    ("simplify: 목록도 '없음'도 아님", "simplify", "실패",
     {"overrides": {"simplify": "# simplify\n\n## 정리 결과\n\n정리했다.\n"}}),

    ("review: 🔴 반영됨", "review", "통과", {}),
    ("review: 🔴 미반영", "review", "실패",
     {"overrides": {"review": REVIEW_GOOD.replace("| 🔴 | 외부 입력 검증 없음 | 반영 |",
                                                  "| 🔴 | 외부 입력 검증 없음 | 미반영 |")}}),
    ("review: 판정 표도 없음 표시도 없음", "review", "실패",
     {"overrides": {"review": "# review\n\n## 판정\n\n리뷰했음.\n"}}),

    ("docs: 정상", "docs", "통과", {}),
    ("docs: 목록도 '없음'도 아님", "docs", "실패",
     {"overrides": {"docs": "# docs\n\n## 문서 영향\n\n확인함.\n"}}),

    ("close: 커밋이 없음", "close", "실패", {"repo": {"empty": True}}),
    ("close: 작성자가 레포 설정과 다름", "close", "실패",
     {"repo": {"author": "someone@example.com"}}),
    ("close: 메시지 형식 위반", "close", "실패",
     {"repo": {"subject": "테스트 변경 추가"}}),
    ("close: 작업트리가 더러움", "close", "실패", {"repo": {"dirty": True}}),

    ("ship: 정상", "ship", "통과", {}),
    ("ship: PR URL 없음", "ship", "실패",
     {"overrides": {"ship": "# ship\n\npush 했음.\n"}}),

    ("close: 정상", "close", "통과", {}),
    ("close: status가 진행중", "close", "실패", {"meta": {"status": "진행중"}}),
    ("close: 리뷰 🔴이 남아 있음", "close", "실패",
     {"overrides": {"review": REVIEW_GOOD.replace("| 🔴 | 외부 입력 검증 없음 | 반영 |",
                                                  "| 🔴 | 외부 입력 검증 없음 | 미반영 |")}}),
]


def run_case(name: str, stage: str, expect: str, spec: dict) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo: Path | str = (make_repo(root, **spec.get("repo", {}))
                            if stage in GIT_STAGES else "(저장소 없음)")
        cycle = root / "cycle"
        overrides = dict(spec.get("overrides") or {})

        make_cycle(cycle, repo, overrides=overrides, meta=spec.get("meta"))
        fails = gate_of(cycle, stage)

    got = "실패" if fails else "통과"
    ok = got == expect
    print(f"{'✅' if ok else '❌'} {name:42s} → {got}")
    if not ok:
        print(f"      기대: {expect} · 사유: {fails}")
    elif expect == "실패":
        print(f"      ↳ {fails[0]}")
    return ok


def test_skip_is_not_an_escape_hatch() -> bool:
    """관문이 막았을 때 상태 칸을 '생략'으로 바꾸는 우회로가 없는지.

    이 부서가 존재하는 이유인 커밋 작성자 검사를, 표 한 칸을 고쳐 스스로
    면제할 수 있으면 안 된다. 파서가 로드 시점에 거절해야 한다.
    """
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        cycle = Path(tmp) / "cycle"
        make_cycle(cycle, "(저장소 없음)", meta={})
        text = (cycle / "handoff.md").read_text(encoding="utf-8")

        # ship은 초안 모드에서 정당하게 생략된다.
        (cycle / "handoff.md").write_text(
            text.replace("| ship | 완료 |", "| ship | 생략 |"),
            encoding="utf-8")
        try:
            handoff.load(cycle)
            print("✅ 생략: ship은 허용된다")
        except handoff.HandoffError as exc:
            print(f"❌ 생략: ship이 거절됐다 — {exc}")
            ok = False

        # close는 안 된다.
        (cycle / "handoff.md").write_text(
            text.replace("| close | 완료 |", "| close | 생략 |"),
            encoding="utf-8")
        try:
            handoff.load(cycle)
            print("❌ 생략: close를 생략으로 통과시켰다")
            ok = False
        except handoff.HandoffError as exc:
            print(f"✅ 생략: close는 거절된다 — {str(exc).split('—')[0].strip()}")
    return ok


def test_decision_log_is_one_line() -> bool:
    """결정 로그 항목이 한 줄을 넘으면 파서가 로드 시점에 거절하는지.

    "한 줄"이라고 템플릿에 적어 두는 것만으로는 지켜지지 않았다 — 실제 사이클의
    항목 하나가 820자 문단이었다. 규칙을 파서로 옮긴 뒤 실제로 막는지 본다.

    저장소를 만들지 않는다 — 이 검사는 마크다운만 본다.
    """
    cases = (
        ("한 줄 항목은 통과",
         "- 2026-01-01 · intake · 이슈 #12를 명세로 정규화. 근거: `00_intake.md`", True),
        ("여러 줄 항목은 거부", "- 2026-01-01 · intake · 첫 줄\n  이어지는 둘째 줄", False),
        (f"{handoff.DECISION_LOG_MAX}자 초과 항목은 거부",
         "- " + "가" * handoff.DECISION_LOG_MAX, False),
    )
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        cycle = Path(tmp) / "cycle"
        make_cycle(cycle, "(저장소 없음)")
        p = cycle / "handoff.md"
        original = p.read_text(encoding="utf-8")
        for name, item, should_load in cases:
            p.write_text(original.replace(
                "## 결정 로그\n", f"## 결정 로그\n\n{item}\n"), encoding="utf-8")
            try:
                handoff.load(cycle)
                loaded = True
            except handoff.HandoffError:
                loaded = False
            p.write_text(original, encoding="utf-8")
            if loaded == should_load:
                print(f"✅ 결정 로그: {name}")
            else:
                print(f"❌ 결정 로그: {name} → {'통과' if loaded else '거부'}됐다")
                ok = False
    return ok


def main() -> int:
    failed = sum(not run_case(*c) for c in CASES)
    print()
    if not test_skip_is_not_an_escape_hatch():
        failed += 1
    print()
    if not test_decision_log_is_one_line():
        failed += 1
    print()
    if failed:
        print(f"{failed}건이 기대와 다르다")
        return 1
    print(f"{len(CASES)}개 케이스 + 생략 우회로 검사, 전부 기대대로 갈렸다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
