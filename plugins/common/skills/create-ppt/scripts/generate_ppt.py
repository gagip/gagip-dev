#!/usr/bin/env python3
"""
개발 브리핑 PPT 조립기
JSON 입력 → slides 배열의 컴포넌트를 순서대로 조립 → HTML 프레젠테이션 출력

JSON 최소 구조:
  { "project_name": "...", "slides": [ {"type": "cover"}, ... ] }

slides 키를 생략하면 기본 18장 프리셋이 사용된다.
각 슬라이드 객체의 데이터 키는 SKILL.md 컴포넌트 카탈로그 참조.
"""

import json
import sys
import argparse
from html import escape as _esc
from pathlib import Path

# components 패키지 import (이 파일과 같은 위치)
sys.path.insert(0, str(Path(__file__).parent))
from components import REGISTRY
from components.base import HEAD, FOOT

# ── 기본 프리셋 (slides 배열 미지정 시 사용) ──────────────────────────────────
# 구성 데이터는 top-level JSON 글로벌에서 자동으로 채워진다.

DEFAULT_PRESET = [
    {'type': 'cover'},
    {'type': 'toc'},
    {'type': 'section',
     'title': '프로젝트 개요',
     'subtitle': '무엇을, 왜 만드는지 — 배경과 목표, 그리고 핵심 기능을 정리합니다.'},
    {'type': 'overview'},
    {'type': 'background'},
    {'type': 'features'},
    {'type': 'section',
     'title': '개발 현황',
     'subtitle': '어디까지 왔는지 — 진행 현황, 핵심 성과, 시스템 구조를 공유합니다.'},
    {'type': 'roadmap'},
    {'type': 'metrics'},
    {'type': 'architecture'},
    {'type': 'tech_stack'},
    {'type': 'section',
     'title': '상세 & 일정',
     'subtitle': '어떻게 만들었고 앞으로 무엇이 남았는지 — 구현 방식과 일정을 정리합니다.'},
    {'type': 'implementation'},
    {'type': 'schedule'},
    {'type': 'before_after'},
    {'type': 'impact'},
    {'type': 'next_steps'},
    {'type': 'closing'},
]


# ── 조립기 ────────────────────────────────────────────────────────────────────

def assemble(d: dict) -> str:
    """JSON 딕셔너리 → HTML 문자열"""
    slides = d.get('slides') or DEFAULT_PRESET

    # 알 수 없는 type 조기 감지
    unknown = [s['type'] for s in slides if s.get('type') not in REGISTRY]
    if unknown:
        raise ValueError(
            f'알 수 없는 슬라이드 type: {unknown}\n'
            f'허용 값: {sorted(REGISTRY.keys())}'
        )

    # ── 사전 패스: section 슬라이드 목록 수집 (toc가 사용) ───────────────────
    sections = []
    sec_idx = 0
    for i, slide in enumerate(slides):
        if slide.get('type') == 'section':
            sec_idx += 1
            sections.append({
                'no':       f'{sec_idx:02d}',
                'title':    slide.get('title', f'섹션 {sec_idx:02d}'),
                'subtitle': slide.get('subtitle', ''),
                'position': i + 1,
            })

    # ── 본 패스: 슬라이드 순회 → 컴포넌트 render 호출 ───────────────────────
    html_parts = []
    current_sec_no = '00'
    current_sec_idx = 0

    for i, slide in enumerate(slides):
        stype = slide.get('type')
        if stype == 'section':
            current_sec_no = sections[current_sec_idx]['no']
            current_sec_idx += 1

        ctx = {
            # top-level 글로벌 (컴포넌트 폴백용)
            'project_name': d.get('project_name', '프로젝트명'),
            'date':         d.get('date', '2026.06'),
            'presenter':    d.get('presenter', '발표자 · 소속'),
            # 조립 시점 정보
            'position':     i + 1,
            'section_no':   current_sec_no,
            'sections':     sections,
            'total':        len(slides),
            # 원본 JSON 전체 (컴포넌트 글로벌 폴백)
            'globals':      d,
        }

        html_parts.append(REGISTRY[stype].render(slide, ctx))

    title = _esc(d.get('project_name', '개발 브리핑')) + ' · 브리핑'
    total = len(slides)
    body  = '\n'.join(html_parts)

    return HEAD.format(title=title) + body + '\n' + FOOT.format(total=total)


# ── 진입점 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='개발 브리핑 HTML PPT 생성')
    parser.add_argument('--input',  '-i', required=True, help='JSON 입력 파일 경로')
    parser.add_argument('--output', '-o', required=True, help='HTML 출력 파일 경로')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f'오류: 입력 파일을 찾을 수 없습니다: {input_path}', file=sys.stderr)
        raise SystemExit(1)

    with open(input_path, encoding='utf-8') as f:
        data = json.load(f)

    html = assemble(data)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding='utf-8')

    total = len(data.get('slides') or DEFAULT_PRESET)
    print(f'✓ 생성 완료: {output_path.resolve()}')
    print(f'  슬라이드: {total}장 | 크기: {len(html) // 1024}KB')


if __name__ == '__main__':
    main()
