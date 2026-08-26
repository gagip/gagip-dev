---
# ── 기계가 읽는 토큰 (Google design.md 스펙 형식) ──
# 관련 없는 축은 생략 가능. name과 최소 primary 색만 필수.
name: <프로젝트> Design System
version: 1.0
description: <한 줄 — 이 시스템의 성격>
colors:
  primary: "#2563EB"
  primary-active: "#1D4ED8"
  canvas: "#F8FAFC"
  surface: "#FFFFFF"
  ink: "#0F172A"
  muted: "#64748B"
  danger: "#DC2626"
typography:
  display: { family: "Poppins" }
  body: { family: "Inter" }
  scale:
    display-xl: { size: 48, weight: 700, lh: 1.1 }
    h2: { size: 28, weight: 600, lh: 1.25 }
    body-md: { size: 16, weight: 400, lh: 1.5 }
    label: { size: 14, weight: 500, lh: 1.4 }
    caption: { size: 12, weight: 400, lh: 1.4 }
spacing: { base: 4, xxs: 4, xs: 8, sm: 12, md: 16, lg: 24, xl: 32, section: 64 }
rounded: { sm: 8, md: 12, pill: 9999 }
components:
  button-primary: { height: 40, padding: "0 16", rounded: 8, bg: primary, text: "#FFFFFF" }
  card: { rounded: 12, padding: 20, bg: surface, shadow: "0 1px 2px rgba(15,23,42,.06)" }
  input: { height: 44, padding: "0 12", rounded: 8, border: "#E2E8F0" }
---

# <프로젝트> Design System

> **사용법** — UI를 생성·수정하기 전에 이 파일을 읽고 아래 토큰·규칙을 따른다. 값은 결정된 것이며, 임의로 다른 값을
> 만들지 않는다. 애매하면 Overview의 톤과 Do's & Don'ts를 기준으로 판단한다.

## Overview / Visual Theme
<브랜드 personality·타깃·감정적 톤 3~5문장. 애매한 케이스의 판단 기준.>

## Colors
| Token | Value | Role | Usage / 금지 |
|---|---|---|---|
| primary | `#2563EB` | 주요 액션·활성 링크 | Primary CTA·활성에만. 한 뷰에 2개 금지 |
| surface | `#FFFFFF` | 카드·시트 배경 | 같은 surface 연속 겹침 금지 |
| canvas | `#F8FAFC` | 페이지 배경 | surface와 대비 유지 |
| ink | `#0F172A` | 본문 텍스트 | 순검정(#000) 금지 |
| muted | `#64748B` | 보조 텍스트 | 본문에 쓰지 않음 |
| danger | `#DC2626` | 오류·파괴적 액션 | 장식용 금지 |

## Typography
- Display: `Poppins` / Body: `Inter`

| Role | Size / Weight / LH | 용도 |
|---|---|---|
| display-xl | 48 / 700 / 1.1 | Hero h1 |
| h2 | 28 / 600 / 1.25 | 섹션 제목 |
| body-md | 16 / 400 / 1.5 | 본문 |
| label | 14 / 500 / 1.4 | 버튼·라벨 |
| caption | 12 / 400 / 1.4 | 보조·메타 |

## Spacing & Layout
- 베이스 단위 4px. 스케일: `xxs 4 · xs 8 · sm 12 · md 16 · lg 24 · xl 32 · section 64`
- 콘텐츠 max-width 1120px, 중앙 정렬. gutter 모바일 16 · 데스크톱 24
- 카드 padding 20 · 카드 간격 16

## Components
### Button — Primary
- height 40 · padding 0 16 · radius 8 · label(14/500)
- 기본 bg `primary`/text white · hover bg `primary-active` · disabled bg `#E2E8F0`/text `muted`
### Card
- bg `surface` · radius 12 · padding 20 · shadow `0 1px 2px rgba(15,23,42,.06)`
### Input
- height 44 · padding 0 12 · radius 8 · border 1px `#E2E8F0` · focus border `primary`

## Do's & Don'ts
### Do
- 강조는 `primary` 하나로, 위계는 크기·여백으로 만든다
- 새 UI는 정의된 컴포넌트를 먼저 찾아 재사용한다
- 색·간격·radius는 항상 토큰에서 가져온다
### Don't
- 순검정(#000)·임의 hex 하드코딩 금지 — 토큰만
- 한 화면에 primary 버튼 2개 금지
- 같은 surface 카드 겹침 금지
- 스케일 밖 임의 사이즈·간격 금지

<!-- ── 권장 섹션 (값이 있으면 추가) ──
## Depth & Elevation   — shadow 스케일 sm/md/lg + 언제 어느 단계
## Responsive Behavior — 브레이크포인트별 그리드·네비 변화
## Accessibility       — 대비 ≥ WCAG AA(4.5:1), 포커스 링, 터치 44px
## Motion              — duration/easing (절제)
## Known Gaps          — 미정의 영역·폰트 대체안
-->

<!-- ══════════════ 부수 산출물 ══════════════
 preview.html — 스와치·타입스케일·컴포넌트 갤러리 + 라이트/다크 토글(단일 파일). 조건부로 생성됨.
     → 그린필드(볼 실앱 없음)면 권장, 브라운필드면 공유·육안검증용으로 옵션 제안. templates/preview.template.html 참고.
 토큰 파일 (아직 미생성) — tokens.json = DTCG 정본($value/$type, 플랫폼 중립) · 소비판 = 감지된 스택용(웹 --ds-* / 네이티브 kt·swift).
     → Tailwind/Style Dictionary 등 빌드 파이프라인이 감지될 때만 별도 emit.
 코어(이 DESIGN.md)를 가볍게 두는 이유: 성숙 프로덕션에선 원시 토큰 인라인 과다가 토큰 과소비·컴포넌트 재생성 부채를 부른다.
═══════════════════════════════════════════════ -->
