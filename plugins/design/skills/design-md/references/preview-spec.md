# preview.html 생성 스펙

SKILL.md의 preview 생성 단계에서 참고한다. `templates/preview.template.html`을 뼈대로, **방금 저장한 DESIGN.md의
값**을 채워 `<root>/preview.html` 하나를 만든다. preview.html은 **사람이 브라우저로 여는 시각 레퍼런스 보드**다 —
스와치·타입스케일·스페이싱·컴포넌트를 한 화면에서 눈으로 검증/공유한다.

> **왜 조건부인가** — 이미 렌더되는 실앱이 있으면 preview는 대체로 중복이다(실앱이 진짜 레퍼런스다). 그래서 기본 생성이
> 아니라, **그린필드(볼 실앱이 없음)** 이거나 **사람이 육안검증·공유를 원할 때** 만든다. SKILL.md의 트리거 규칙을 따른다.

## 절대 규칙

1. **자기완결.** 외부 폰트·CSS·JS·이미지·CDN을 **절대 참조하지 않는다**. 모든 스타일/스크립트는 인라인. 오프라인에서
   파일을 더블클릭하면 그대로 열려야 한다. (브랜드 웹폰트가 있어도 `@import`/`<link>` 금지 — `font-family` 이름만 쓰고
   `system-ui` 폴백을 남긴다. 폰트 부재는 Known Gaps로 이미 문서화돼 있다.)
2. **값은 DESIGN.md와 100% 일치.** preview는 DESIGN.md의 시각화일 뿐이다. hex·px·서체를 임의로 바꾸지 않는다.
   프론트매터/본문 표에 있는 값을 그대로 옮긴다.
3. **손으로 편집하는 파일이 아님.** 푸터 문구를 남겨 "DESIGN.md를 고친 뒤 재생성"임을 명시한다.

## 섹션별 채우기

템플릿의 각 `FILL:` 주석 위치를 대상 값으로 교체한다. 구조·CSS 스캐폴딩·토글 스크립트는 **그대로 둔다**.

- **:root 브랜드 토큰** — 템플릿 상단 `/* ══ 브랜드 토큰 ══ */` 블록의 `--brand-*` 변수를 DESIGN.md frontmatter
  `colors`/`rounded`/`typography.*.family` 실제 값으로 교체한다. 컴포넌트·스와치가 이 변수를 참조하므로 여기만 바꾸면
  대부분 반영된다. 시맨틱 토큰명이 `primary`가 아니면(예: `accent`) `--brand-primary`→`--brand-accent`처럼 **변수명을
  DESIGN.md 토큰명에 맞춰 리네임해도 된다**(전 참조 일괄 치환). 이는 시맨틱 명확성이지 스캐폴딩 훼손이 아니다 — 유지해야
  할 "스캐폴딩"은 CSS 구조·토글 스크립트·레이아웃이지 변수명이 아니다.
- **Colors** — DESIGN.md `Colors` 표의 토큰마다 `.swatch` 하나. `chip` 배경 = 실제 hex, `name`/`hex`/`role`을 표에서
  옮긴다. 흰색·아주 밝은 색 chip은 템플릿처럼 `border-bottom`을 줘 배경과 구분한다. 토큰 수만큼 늘리거나 줄인다.
- **Typography** — 각 role을 **실제 size/weight/line-height로 렌더**한 specimen 행. 라벨은 `role · size/weight`.
  display 행엔 `font-family:var(--brand-font-display)`를 준다. specimen 문구는 자유(한글/영문 섞어 가독성 확인).
- **Spacing** — 스케일 스텝마다 `.space-row`, `bar`의 `width`를 실제 px로. 베이스 단위·max-width는 상단 note에.
- **Components** — DESIGN.md `Components` 섹션의 실제 값으로. 버튼은 기본/active(=hover 색)/disabled 세 상태를 나란히.
  카드·인풋은 radius·padding·border를 브랜드 변수로. 정의된 컴포넌트가 더 있으면(badge·chip 등) `.stage`에 추가한다.

## 다크 토글 처리 (핵심 — 열망 금지)

DESIGN.md에 **다크 팔레트가 실제로 정의돼 있는지**로 갈린다:

- **다크 토큰 있음** (frontmatter에 `colors.dark` 블록, 또는 `canvas-dark`/`surface-dark`/`ink-dark` 류가 있음)
  → 템플릿의 `[A]` 블록 주석을 풀고 그 다크 값으로 `html[data-theme="dark"]`의 `--brand-*`를 채운다. 토글이 브랜드
  렌더까지 다크로 스왑한다. 헤더 `data-darknote` 문구를 "다크 팔레트 반영"으로 바꾼다.
- **다크 토큰 없음** (대부분) → `[A]` 블록을 **삭제한 채로 둔다**. 토글은 페이지 배경(크롬)만 전환해, 같은 브랜드 색을
  밝은/어두운 주변에서 대조하게 한다. **다크 색을 지어내지 않는다.** `data-darknote`는 템플릿 기본 문구("토글은 페이지
  배경만 전환합니다 (다크 팔레트 미정의)")를 유지한다.

## 저장 + 검증

- `<root>/preview.html`로 `Write`한다. DESIGN.md 옆(프로젝트 루트)에 둔다.
- 저장 후 자체 점검: ① 외부 참조가 하나도 없는가(`http`/`//`/`@import`/`<link`/`src=` grep으로 확인), ② 스와치 hex가
  DESIGN.md와 일치하는가, ③ 컴포넌트가 브랜드 변수를 참조하는가.
- 사용자에게 "브라우저로 `preview.html`을 열어 확인하라"고 안내한다. 커밋·push는 하지 않는다.
