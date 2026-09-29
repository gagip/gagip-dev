"""평가 픽스처 조립 — 채점기가 실제로 통과·실패를 가르는지 확인할 예시를 만든다.

핸드오프는 템플릿을 복사해 고친다. 단계 목록을 여기서 다시 적으면
파이프라인 정의와 갈리므로, 정본은 언제나 assets/cycle-template/handoff.md다.
"""

from __future__ import annotations

import re
from pathlib import Path

import handoff
import paths

TEMPLATE = paths.TEMPLATE_HANDOFF


def write_cycle(
    dest: Path,
    meta: dict[str, str],
    stages: dict[str, tuple[str, str]],
    drop: tuple[str, ...] = (),
) -> Path:
    """dest에 핸드오프를 쓴다.

    meta:   머리말에서 덮어쓸 키
    stages: {단계키: (상태, 산출물)}
    drop:   머리말에서 지울 키 — 옛 형식 사이클을 흉내 낸다
    """
    dest.mkdir(parents=True, exist_ok=True)
    text = TEMPLATE.read_text(encoding="utf-8")

    for key, value in meta.items():
        text = handoff.set_meta(text, key, value)

    for key in drop:
        text, n = re.subn(rf"^{re.escape(key)}:.*\n", "", text, count=1, flags=re.MULTILINE)
        if n != 1:
            raise KeyError(f"머리말에 지울 '{key}' 키가 템플릿에 없다")

    for key, (state, artifact) in stages.items():
        # [^|\n] — 개행을 빼지 않으면 표가 깨졌을 때 두 줄을 한 줄로 합쳐 버린다.
        row = f"| {key} | {state} | {artifact} |"
        text, n = re.subn(rf"^\|\s*{re.escape(key)}\s*\|[^|\n]*\|[^|\n]*\|$",
                          lambda _m: row, text, count=1, flags=re.MULTILINE)
        if n != 1:
            raise KeyError(f"진행 표에 단계 '{key}' 행이 없다")

    (dest / "handoff.md").write_text(text, encoding="utf-8")
    return dest
