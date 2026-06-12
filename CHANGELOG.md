# CHANGELOG

## [common/0.8.4] — 2026-06-12

### ✨ New Features
- `apply-review` 리뷰 보고서 저장을 Notion Report DB 우선으로 전환 — 보고서를 `유형=분석 · 상태=초안`으로 Notion Report DB에 우선 생성하고, 자율 실행 완료 후 같은 페이지를 갱신(상태→검토중, "처리 결과" 추가). Notion 미셋업·로컬 요청 시 기존 파일 경로(`review-report-PR{N}-{YYYYMMDD}.md`)로 폴백 ([`6cfcfd6`])

### 🐛 Bug Fixes
- `apply-review` allowed-tools에 Notion MCP 도구(`notion-create-pages`·`notion-fetch`·`notion-update-page`) 추가 — 본문이 지시하는 노션 우선 저장 경로가 실제 동작하도록 정합성 확보 ([`7a2e96b`])

---

## [common/0.8.3] — 2026-06-11

### ✨ New Features
- 스킬에 "스파이크 사전 검증 게이트" 개념 추가 — `draft-plan`: 실험으로만 판정 가능한 미검증 전제(외부 SDK·플랫폼·비동기 동작 등)는 본 작업 전 커밋 0(스파이크 게이트)로 검증하도록 규칙·계획서 템플릿(`## 기술 리스크 / 스파이크`)·커밋 계획에 반영. `setup-skills/testing`: 스파이크를 "만들기 전 가정 검증"으로 정의하고, 통과 기준에 검증 대상 경로 실제 통과 여부·타임박스를 박도록 명시 ([`3551357`])

---

## [common/0.8.2] — 2026-06-11

### ✨ New Features
- `draft-plan` 계획서 구조를 목표 → 목표 달성 기준 → 구현 성공 기준 → 검증의 4층 흐름으로 재편 — 구현 성공 기준과 검증(확인 방법)을 명확히 분리하고 각 층을 상호 매핑하도록 명시 ([`49e1c99`])
- `draft-plan`에 `WebSearch`/`WebFetch` 추가 — 외부 근거 조사를 허용하되 출처(URL) 명시 의무화 ([`49e1c99`])

### ♻️ Refactoring
- `draft-plan` 승인 흐름 변경 — `ExitPlanMode` 승인 게이트 제거, 초안 완성 시 `notion-report`로 즉시 자동 저장하고 피드백은 노션 댓글로 받도록 전환 ([`49e1c99`])

---

## [common/0.8.1] — 2026-06-10

### ✨ New Features
- `draft-plan` 구현계획 보고서에 코드 발췌·자립 구성 원칙 추가 — 보고서 골격에 "한눈에 / 배경지식" 섹션 추가, 현황 분석을 줄번호 대신 코드 발췌로 증명하도록 변경, 코드를 열어보지 않는 독자도 단독 이해 가능하도록 자립 구성 명시 ([`e45b1d4`])

---

## [common/0.7.0] — 2026-06-10

### ✨ New Features
- `notion-context`·`notion-knowledge`·`notion-report` 스킬 3종 추가 — 대화 결정사항을 Notion Context DB에 누적 반영, Knowledge DB 검색, 작업 보고서를 Reports DB에 작성 ([`a585655`])
- `draft-plan` 구현 방식 대안을 판단 기준과 함께 비교 제시하는 규칙 추가 ([`bdb5ff9`])
- `create-pr`·`report-issue` 본문에서 private 정보 제외 규칙 추가 ([`38e1539`])
- `retrospective` 다중 세션·주간/기간 단위 회고 워크플로우 추가 ([`2504ef4`])

### 🐛 Bug Fixes
- `notion` 스킬 MCP 도구명 정정(`fetch`→`notion-fetch`, `search`→`notion-search`) 및 `notion-report` 파일명 `SKILL.md`로 통일 — 대소문자 구분 FS 호환 ([`fe1af0f`])
- `retrospective` `allowed-tools`에 `Agent` 추가 ([`e92aefd`])

### ♻️ Refactoring
- `draft-plan` 계획서 저장을 `notion-report` 스킬로 위임 ([`aded3d7`])

---

## [common/0.6.2] — 2026-06-05

### ✨ New Features
- `draft-plan` 계획서 골격에 `## 코드 리뷰` 게이트 섹션 추가 — 구현·검증·커밋 완료 후 `/code-review medium`(및 커스텀 리뷰 스킬) 실행을 지시, 위험 지적만 수정하도록 명시 ([`b053654`])

---

## [common/0.6.1] — 2026-06-02

### 🐛 Bug Fixes
- `retrospective` 볼트 기록을 회사/개인으로 분리, 하드코딩된 경로를 CLAUDE.md 참조 방식으로 변경 ([`855e488`])

---

## [common/0.5.2] — 2026-04-20

### ♻️ Refactoring
- `setup-skills` VSA Flutter 아키텍처 문서 업데이트 및 폴더 구조 정리 ([`ab38e8f`])

---

## [common/0.4.0] — 2026-03-22

### ♻️ Refactoring
- 플러그인 핵심 워크플로 스킬만 유지 — `implement`, `create-issue`, `write-report` 등 제거, `apply-review`·`commit`·`create-pr`·`setup-skills` 유지 ([`20941a6`])

### 🐛 Bug Fixes
- `setup-skills` 스킬 설명·트리거·지침 개선 ([`2a45fb0`])

---

## [android/0.4.0] — 2026-03-22

### ♻️ Refactoring
- 플러그인 리뷰/테스트 스킬만 유지 — 기존 스킬 정리 ([`14da819`])

### 🐛 Bug Fixes
- `reference` 문서를 기술 철학에 맞게 수정 ([`bb39a0e`])

---

## [android/0.3.1] — 2026-03-18

### ✨ New Features
- `write-test` 스킬에 테스트 시나리오 서술 가이드라인 추가 — 내부 상태값/메서드명 직접 노출 금지, 사용자 동작과 관찰 가능한 결과로 서술 ([`6fcd3c6`])

## [common/0.2.2] — 2026-03-14

### 🐛 Bug Fixes
- 훅 실행 명령을 `python3` → `python`으로 변경 (Windows 호환) ([`e62549f`])
- `validate_commit` 훅의 HEREDOC 커밋 메시지 파싱 순서 수정 ([`6c5418e`])
- 커밋 스킬 `allowed-tools`에 `Read` 추가 ([`41d81ce`])

### ✨ New Features
- `release` 스킬 플러그인 및 버전 자동 감지로 개선 ([`059bef6`])

## [0.2.0] — 2026-03-13

### ✨ New Features
- `skill-consistency-reviewer` 에이전트 추가 — 전체 스킬 간 일관성 일괄 점검 ([`f194680`])
- `apply-review`, `commit`, `create-issue`, `create-pr` 스킬에 행동 원칙 섹션 추가 ([`37a7534`])
- `implement`, `create-issue` 스킬에 `argument-hint` 추가 ([`13694a7`])
- `write-report` 스킬을 AI 전용(`user-invocable: false`)으로 전환 ([`13694a7`])

### 🐛 Bug Fixes
- `validate_commit` 훅을 커밋 후 경고에서 커밋 전 차단 방식으로 전환 ([`13694a7`])
- `hooks.json`의 중복 이벤트 선언 제거 및 `PreToolUse`로 통합 ([`e5a6f7c`])

### ♻️ Refactoring
- `implement` 스킬의 `[STOP × N]` 표기를 `[STOP]`으로 통일 ([`37a7534`])
- `write-report` 스킬의 섹션명 `## 원칙` → `## 행동 원칙` 통일 ([`37a7534`])
- `review-code` 스킬의 종료 조건을 산문에서 `[STOP]` 태그로 명시 ([`37a7534`])
- `skill-consistency-reviewer`의 스킬 탐색 경로에 `plugins/*/skills/*/SKILL.md` 추가 ([`37a7534`])

### 🔧 Chores
- `block_sensitive_files` 훅의 `.env` 패턴을 `startswith` 방식으로 강화 ([`354888c`], [`37a7534`])
- `common`, `android` 플러그인 버전 `0.1.0` → `0.2.0` ([`2b630c5`])
