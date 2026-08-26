# DESIGN.md 섹션 상세 스펙 + 스캔 패턴

SKILL.md의 Step 2(값 추출)·Step 3(작성)에서 참고한다. 두 부분으로 구성:
- **A. 축별 스캔 패턴** — 브라운필드에서 실제 값을 뽑는 grep/glob
- **B. 섹션별 형식 + granularity 예시** — 무엇을 얼마나 촘촘하게 쓰나

예시의 색·수치는 모두 **일반 예시**다. 실제 산출물에는 대상 프로젝트에서 스캔/합의한 값을 넣는다.

---

## A. 축별 스캔 패턴 (브라운필드)

목표는 "코드에 실제로, 자주, 의미 있게 쓰인 값"을 뽑는 것이다. 일회성 값은 토큰이 아니다 — 빈도와 역할로 승격 여부를 정한다.

### A-1. 컬러

```bash
# CSS 커스텀 프로퍼티 정의 (--color-*, --bg-*, --text-* 등)
grep -rhoE -- '--[a-z0-9-]+:\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\))' src app 2>/dev/null | sort | uniq -c | sort -rn | head -40

# 원시 색 리터럴 빈도 (자주 나오는 hex = 토큰 후보)
grep -rhoE '#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b' src app 2>/dev/null | tr 'A-F' 'a-f' | sort | uniq -c | sort -rn | head -40

# Tailwind 팔레트 (theme.colors / theme.extend.colors)
sed -n '/colors\s*:/,/}/p' tailwind.config.* 2>/dev/null
```
- 뽑을 것: 값 + **역할**(배경/텍스트/테두리/강조/의미색). 역할은 클래스명·변수명·사용 위치에서 읽는다(`--bg-surface`, `text-danger`).
- 승격: 빈도 상위 + 명확한 역할을 가진 색만 시맨틱 토큰으로. 40개 hex 중 실제 토큰은 대개 6~12개다.

### A-2. 타이포그래피

```bash
# 서체
grep -rhoE 'font-family\s*:[^;]+;' src app 2>/dev/null | sort | uniq -c | sort -rn
grep -rEl 'next/font|@font-face|StyleSheet|fontFamily' src app 2>/dev/null | head
# 사이즈 스케일 (반복되는 font-size / fontSize)
grep -rhoE 'font-size\s*:\s*[0-9.]+(px|rem|em)|fontSize:\s*[0-9]+' src app 2>/dev/null | sort | uniq -c | sort -rn | head
```
- 뽑을 것: display/body 서체, weight, 그리고 사이즈를 **용도별로 명명**(Hero h1 / Section h2 / Body / Label / Caption).
- `font-size: 3rem` 같은 raw 나열이 아니라 `Hero h1 = 48px / 600` 처럼 크기↔용도↔weight를 묶는다.

### A-3. 스페이싱 / 레이아웃

```bash
# 반복 padding/margin 값 → 베이스 단위·스케일 추정
grep -rhoE '(padding|margin|gap)\s*:\s*[0-9.]+(px|rem)' src app 2>/dev/null | grep -oE '[0-9.]+(px|rem)' | sort | uniq -c | sort -rn | head
grep -rhoE 'max-width\s*:\s*[0-9]+px|container' src app 2>/dev/null | sort | uniq -c | sort -rn | head
sed -n '/spacing\s*:/,/}/p' tailwind.config.* 2>/dev/null
```
- 뽑을 것: 베이스 단위(대개 4 또는 8px), 스케일(xxs~xxl), 콘텐츠 max-width, 그리드/컨테이너 규칙.

### A-4. 컴포넌트

```bash
# 버튼·인풋·카드 등 반복 컴포넌트의 실제 스타일
grep -rEl 'button|btn|card|input|modal|badge|chip' src app 2>/dev/null | head
# radius / shadow 스케일
grep -rhoE 'border-radius\s*:\s*[0-9.]+(px|rem|%)|borderRadius:\s*[0-9]+' src app 2>/dev/null | sort | uniq -c | sort -rn | head
grep -rhoE 'box-shadow\s*:[^;]+;' src app 2>/dev/null | sort | uniq -c | sort -rn | head
```
- 뽑을 것: 각 컴포넌트의 height·padding·radius·shadow·상태(hover/active/disabled)를 **절대값**으로.

> 스캔이 애매하거나 스택이 특이하면(예: CSS-in-JS 테마 객체, 디자인 토큰 SDK), 관련 파일을 Read로 직접 읽어 값을 확인한다.
> grep은 후보를 좁히는 도구일 뿐, 최종 값은 실제 정의를 확인해 확정한다.

---

## B. 섹션별 형식 + granularity 예시

### B-1. Overview / Visual Theme (필수)

3~5문장. 브랜드 personality, 타깃, 감정적 톤. 애매한 케이스에서 에이전트가 기댈 판단 기준이 된다.

```markdown
## Overview
차분하고 신뢰감 있는 헬스케어 톤. 밝은 캔버스 위에 절제된 강조색 하나로 위계를 만든다.
장식보다 여백과 타이포의 위계로 정보를 정리한다. 타깃은 자기 건강 데이터를 확인하는 일반 사용자로,
의료적 과장 없이 담백하게 사실을 전달한다.
```

### B-2. Colors (필수)

토큰마다 **값 + 역할 + 사용/금지**. 표로.

```markdown
## Colors
| Token | Value | Role | Usage / 금지 |
|---|---|---|---|
| primary | `#2563EB` | 주요 액션·활성 링크 | Primary CTA·활성 상태에만. 한 뷰에 primary 버튼 2개 금지 |
| primary-active | `#1D4ED8` | primary의 눌림 상태 | hover/active에만 |
| surface | `#FFFFFF` | 카드·시트 배경 | 같은 surface를 연속 겹쳐 쌓지 않는다 |
| canvas | `#F8FAFC` | 페이지 배경 | 카드와 대비를 위해 surface보다 어둡게 유지 |
| ink | `#0F172A` | 본문 텍스트 | 순검정(#000) 금지 |
| muted | `#64748B` | 보조 텍스트·placeholder | 본문에 쓰지 않는다(대비 부족) |
| danger | `#DC2626` | 오류·파괴적 액션 | 강조 장식용으로 쓰지 않는다 |
```

### B-3. Typography (필수)

용도별 명명 + weight/line-height.

```markdown
## Typography
- Display 서체: `Poppins` / Body 서체: `Inter`
| Role | Size / Weight / LH | 용도 |
|---|---|---|
| display-xl | 48px / 700 / 1.1 | Hero h1 |
| h2 | 28px / 600 / 1.25 | 섹션 제목 |
| body-md | 16px / 400 / 1.5 | 본문 |
| label | 14px / 500 / 1.4 | 버튼·폼 라벨 |
| caption | 12px / 400 / 1.4 | 보조 설명·메타 |
```

### B-4. Spacing & Layout (필수)

```markdown
## Spacing & Layout
- 베이스 단위: 4px. 스케일: `xxs 4 · xs 8 · sm 12 · md 16 · lg 24 · xl 32 · section 64`
- 콘텐츠 max-width: 1120px, 중앙 정렬. 좌우 gutter: 모바일 16px · 데스크톱 24px
- 카드 내부 padding: 20px. 카드 사이 간격: 16px
```

### B-5. Components (필수)

절대값 + 상태.

```markdown
## Components
### Button — Primary
- height 40px · padding 0 16px · radius 8px · label(14/500)
- 기본: bg `primary`, text white / hover: bg `primary-active` / disabled: bg `#E2E8F0`, text `muted`
### Card
- bg `surface` · radius 12px · padding 20px · shadow `0 1px 2px rgba(15,23,42,.06)`
### Input
- height 44px · padding 0 12px · radius 8px · border 1px `#E2E8F0` / focus: border `primary`
```

### B-6. Do's & Don'ts (필수 — 최대 레버)

구체적 행동 규칙. 형식·예문은 `dos-and-donts-bank.md` 참고.

```markdown
## Do's & Don'ts
### Do
- 강조는 primary 하나로. 위계는 크기·여백으로 만든다
- 텍스트는 ink/muted 두 단계만 사용
### Don't
- 순검정(#000)·순백 위 순검정 대비 금지 — ink/canvas 토큰 사용
- 한 화면에 primary 버튼 2개 금지
- 카드 위에 카드를 같은 surface로 겹치지 않는다
- 그림자를 3단계 넘게 쓰지 않는다
```

### 권장 섹션 (값이 있으면)
- **Depth & Elevation**: shadow 스케일(sm/md/lg)과 언제 어느 단계를 쓰는지.
- **Responsive Behavior**: 브레이크포인트(예: 640/1024px)별 그리드·네비 변화.
- **Accessibility**: 본문 대비 ≥ WCAG AA(4.5:1), 포커스 링 규칙, 최소 터치 타깃 44px.

### 선택 섹션
- **Motion**: duration(예: 150/250ms) + easing(cubic-bezier). 과하면 AI 생성 티가 나므로 절제.
- **Known Gaps**: 라이선스 폰트 대체안, 아직 미정의 영역을 명시(에이전트가 임의 확장하지 않도록).
