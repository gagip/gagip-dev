"""
컴포넌트 레지스트리
type 문자열 → 모듈 매핑. 각 모듈은 render(slide, ctx) -> str 을 구현한다.
"""

from . import (
    cover, toc, section,
    overview, background, features,
    roadmap, metrics, architecture, tech_stack,
    implementation, schedule, before_after,
    impact, next_steps, closing,
)

REGISTRY: dict = {
    'cover':          cover,
    'toc':            toc,
    'section':        section,
    'overview':       overview,
    'background':     background,
    'features':       features,
    'roadmap':        roadmap,
    'metrics':        metrics,
    'architecture':   architecture,
    'tech_stack':     tech_stack,
    'implementation': implementation,
    'schedule':       schedule,
    'before_after':   before_after,
    'impact':         impact,
    'next_steps':     next_steps,
    'closing':        closing,
}

__all__ = ['REGISTRY']
