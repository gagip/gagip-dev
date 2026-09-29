"""핸드오프 파일 파싱 — 사이클의 상태 객체.

한 사이클의 진행 상태는 `<사이클 폴더>/handoff.md` 한 파일에만 있다.
사람이 열어 직접 고칠 수 있어야 하므로 마크다운을 정본으로 두고,
이 모듈이 그 마크다운을 기계가 읽는 형태로 옮긴다.

파싱 계약:
- 머리말은 `key: value` 평평한 스칼라만 받는다. 중첩·목록은 즉시 실패시킨다.
  (조용히 잘못 읽는 것보다 멈추는 편이 싸다)
- 진행 표의 단계 집합은 STAGES와 정확히 일치해야 한다.
- 진행 표는 3열(단계·상태·산출물)이다. 코드가 안 읽는 칸은 두지 않는다.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import mdsec  # noqa: E402

HANDOFF_FILENAME = "handoff.md"


class HandoffError(Exception):
    """핸드오프 파일이 계약을 어겼다. 호출자가 사용자에게 그대로 보여준다."""


# ── 파이프라인 정의 ─────────────────────────────────────────────
# 이 목록이 곧 작업 그래프다. 순서가 실행 순서이고,
# 핸드오프 표의 행 순서와 일치해야 한다.

@dataclass(frozen=True)
class Stage:
    key: str
    name: str
    kind: str  # 결정 | 실행 | 인계 | 검증 | 종료
    # 이 단계를 '생략'으로 닫아도 되는가. 기본은 안 된다 — 상태 칸에 '생략'이라고
    # 쓰는 것만으로 관문을 면제받을 수 있으면, 모델이 막힌 단계를 고치는 대신
    # 생략으로 바꾸는 길이 열린다. 초안 모드에서 push·PR을 안 하는 ship만 예외다.
    skippable: bool = False


STAGES: tuple[Stage, ...] = (
    Stage("intake",    "작업 명세 정규화",  "결정"),
    Stage("branch",    "브랜치·작업 위치",  "결정"),
    Stage("implement", "구현",              "실행"),
    Stage("simplify",  "정리",              "실행"),
    Stage("review",    "코드 리뷰",         "검증"),
    Stage("docs",      "문서 영향 점검",    "검증"),
    Stage("ship",      "push·PR",           "인계", skippable=True),
    Stage("close",     "사이클 종료",       "종료"),
)

STAGE_KEYS = tuple(s.key for s in STAGES)
STAGE_NAMES = {s.key: s.name for s in STAGES}

# 단계 상태. 관문 통과 여부는 표에 적지 않는다 — gate.py를 돌리면 그 자리에서
# 판정한다. 손으로 적어 둔 판정은 코드가 읽지 않는 낡은 사본이라, 파일이 실제와
# 어긋나도 아무도 모른다. 같은 이유로 "부분"(시작했으나 관문을 못 넘음)도 없앴다 —
# first_incomplete가 미완과 똑같이 취급했으므로 사람만 갈라 적던 값이다.
STATE_DONE, STATE_TODO, STATE_SKIPPED = "완료", "미완", "생략"
STATES = (STATE_DONE, STATE_TODO, STATE_SKIPPED)

# 결정 로그 항목의 글자 수 한도. 한 줄에 "무엇을 · 왜 · 누가 정했나"가 들어가는
# 길이다. 넘으면 그 단계의 산출물 파일에 있어야 할 설명을 로그로 옮겨 적고 있다는
# 뜻이고, 그러면 같은 내용이 두 곳에 생겨 한쪽만 고쳐질 때 갈린다.
DECISION_LOG_MAX = 200

# 사이클 종결값. '불가능'은 사람이 판단해 닫는다.
STATUS_OPEN = "진행중"
STATUS_DONE = "달성"
STATUS_IMPOSSIBLE = "불가능"
STATUSES = (STATUS_OPEN, STATUS_DONE, STATUS_IMPOSSIBLE)

REQUIRED_KEYS = (
    "cycle_id", "title", "opened", "status",
    "repo", "branch", "base", "allow_main",
)

SKIPPABLE_KEYS = frozenset(s.key for s in STAGES if s.skippable)


@dataclass
class StageRow:
    """진행 표의 한 행. 표에 적는 칸은 셋뿐이다 — 단계·상태·산출물.

    단계 이름은 STAGES가 이미 갖고 있어 파일에 다시 적지 않는다.
    """

    key: str
    state: str
    artifact: str

    @property
    def name(self) -> str:
        return STAGE_NAMES[self.key]


@dataclass
class Handoff:
    path: Path
    meta: dict[str, str]
    stages: list[StageRow]

    @property
    def cycle_dir(self) -> Path:
        return self.path.parent

    def stage(self, key: str) -> StageRow:
        for row in self.stages:
            if row.key == key:
                return row
        raise HandoffError(f"단계 '{key}'가 진행 표에 없다")

    def first_incomplete(self) -> StageRow | None:
        """다음 세션이 이어서 할 첫 단계. 없으면 None(전부 완료·생략)."""
        for row in self.stages:
            if row.state == STATE_TODO:
                return row
        return None



_FRONT_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_SCALAR_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$")
_ROW_RE = re.compile(r"^\|(.+)\|\s*$")


def _parse_front_matter(text: str, path: Path) -> dict[str, str]:
    m = _FRONT_RE.match(text)
    if not m:
        raise HandoffError(f"{path}: `---`로 감싼 머리말이 파일 맨 앞에 없다")

    meta: dict[str, str] = {}
    for lineno, raw in enumerate(m.group(1).splitlines(), start=2):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if raw[:1] in (" ", "\t") or line.lstrip().startswith("- "):
            raise HandoffError(
                f"{path}:{lineno}: 머리말은 평평한 `key: value`만 받는다 "
                f"(중첩·목록 불가) — {line!r}"
            )
        sm = _SCALAR_RE.match(line)
        if not sm:
            raise HandoffError(f"{path}:{lineno}: `key: value` 형식이 아니다 — {line!r}")
        key, value = sm.group(1), sm.group(2).strip()
        if key in meta:
            raise HandoffError(f"{path}:{lineno}: 키 '{key}'가 두 번 나온다")
        meta[key] = value

    missing = [k for k in REQUIRED_KEYS if k not in meta]
    if missing:
        raise HandoffError(f"{path}: 머리말에 필수 키가 없다 — {', '.join(missing)}")
    if meta["status"] not in STATUSES:
        raise HandoffError(
            f"{path}: status는 {'/'.join(STATUSES)} 중 하나여야 한다 — {meta['status']!r}"
        )
    return meta


def _parse_stage_table(text: str, path: Path) -> list[StageRow]:
    """`## 진행` 절의 표만 읽는다.

    문서 전체에서 파이프 행을 줍던 때는 열이 6개라 우연 매칭이 사실상 없었지만,
    3열 표는 마크다운에서 흔하다 — 다른 절의 표 한 줄이 단계 행으로 잡히면
    "단계가 파이프라인 정의와 다르다"는 엉뚱한 자리를 가리키는 오류가 난다.
    """
    body = mdsec.section(text, "진행")
    if body is None:
        raise HandoffError(f"{path}: `## 진행` 절이 없다")

    rows: list[StageRow] = []
    for raw in body.splitlines():
        m = _ROW_RE.match(raw.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if cells[0] in ("단계", "") or set(cells[0]) <= set("-: "):
            continue
        if len(cells) != 3:
            raise HandoffError(
                f"{path}: 진행 표는 3열(단계·상태·산출물)이어야 한다 — "
                f"{len(cells)}열인 행이 있다: {raw.strip()!r}"
            )
        key = cells[0]
        if key == "commit":
            raise HandoffError(
                f"{path}: 이전 commit 단계가 남아 있다 — 산출물 참조를 결정 로그에 보존한 뒤 "
                "진행 표의 commit 행만 제거한다"
            )
        if key not in STAGE_KEYS:
            continue
        rows.append(StageRow(key=key, state=cells[1], artifact=cells[2]))

    found = [r.key for r in rows]
    if found != list(STAGE_KEYS):
        raise HandoffError(
            f"{path}: 진행 표의 단계가 파이프라인 정의와 다르다\n"
            f"  파일: {found}\n  정의: {list(STAGE_KEYS)}"
        )
    for row in rows:
        if row.state not in STATES:
            raise HandoffError(
                f"{path}: 단계 '{row.key}'의 상태가 {'/'.join(STATES)} 중 하나가 아니다 — {row.state!r}"
            )
        if row.state == STATE_SKIPPED and row.key not in SKIPPABLE_KEYS:
            raise HandoffError(
                f"{path}: 단계 '{row.key}'는 생략할 수 없다 — 생략 가능한 단계는 "
                f"{', '.join(sorted(SKIPPABLE_KEYS))}뿐이다. 관문이 막으면 고쳐서 넘는다"
            )
    return rows


def _parse_decision_log(text: str, path: Path) -> None:
    """결정 로그는 항목당 `- `로 시작하는 한 줄. 긴 설명은 산출물 파일에 둔다.

    템플릿에 "한 줄"이라고 적어 두는 것만으로는 지켜지지 않았다 — 2026-08-27
    측정화면 사이클은 항목 하나가 400자, iOS 기기모델 사이클은 820자 문단이었다.
    글자로만 있는 규칙은 확률적으로 무시되므로 파일을 읽는 자리에서 거절한다.

    관문(gate.py)이 아니라 여기 두는 이유: 이건 단계 판정이 아니라 handoff.md의
    형식 계약이고, 형식 계약은 전부 이 파서가 로드 시점에 막는다. 관문에 두면
    gate.py를 안 거치는 호출자(회귀 채점기 등)가 규칙 밖으로 빠져나간다.
    """
    body = mdsec.section(text, "결정 로그")
    if body is None:
        raise HandoffError(f"{path}: `## 결정 로그` 절이 없다")
    for raw in body.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if not line.startswith("- "):
            raise HandoffError(
                f"{path}: 결정 로그 항목은 `- `로 시작하는 한 줄이어야 한다 — "
                f"{line.strip()[:40]!r}"
            )
        if len(line) > DECISION_LOG_MAX:
            raise HandoffError(
                f"{path}: 결정 로그 항목이 {len(line)}자다(한도 {DECISION_LOG_MAX}) — "
                f"긴 설명은 그 단계의 산출물 파일에 두고 로그엔 결론만 남긴다: "
                f"{line[:40]!r}"
            )


def parse(text: str, path: Path) -> Handoff:
    _parse_decision_log(text, path)
    return Handoff(path=path, meta=_parse_front_matter(text, path),
                   stages=_parse_stage_table(text, path))


def load(cycle_dir: Path) -> Handoff:
    path = Path(cycle_dir) / HANDOFF_FILENAME
    if not path.is_file():
        raise HandoffError(f"{path}: 핸드오프 파일이 없다")
    return parse(path.read_text(encoding="utf-8"), path)
