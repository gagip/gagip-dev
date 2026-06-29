# CHANGELOG

## [common/0.13.1] — 2026-06-29

### ♻️ Refactoring
- `retrospective` 메모리 처리를 "후보 식별 후 위임"에서 "적격성 게이트 통과분 자동 전달"로 변경 — 재사용성·비자명성·durable·타입적합·행동변화 5개 게이트를 모두 통과한 후보만 사용자 확인 없이 `memory-curator`에 자동 전달. retrospective 게이트(품질)와 memory-curator 필터(중복)로 역할을 분리하고, 메모리 외 항목(스킬·볼트·문서화)은 기존대로 사용자 확인을 유지. `allowed-tools`에 `Skill` 추가 ([`73b1f2c`])

---

## [common/0.13.0] — 2026-06-23

### ✨ New Features
- `review-pack` 스킬 추가 — 작업 끝에 IDE를 열지 않고 문서 하나로 리뷰를 끝내는 "리뷰 팩"(변경 요약 · 핵심 코드 인라인 발췌 · 시각 확인 · 검증 결과 + 🧑리뷰 가이드) 생성. 발췌는 diff 기본 + 새 로직은 최종 코드, push/PR은 리뷰 통과 후. "마지막으로 검토만 하자" 같은 마무리 검토형 발화에도 트리거 ([`9dae9c3`])

### ♻️ Refactoring
- `draft-plan` — 근본 결정 사안이 외부 블로커(팀 확인 등)로 막히면 그때까지의 조사·검증 결과를 계획서 초안(`status: 보류`)으로 먼저 저장하는 가이드 추가. 조기 이탈 시 조사 휘발·재실행 방지 ([`12c29da`])

---

## [common/0.12.0] — 2026-06-23

### ✨ New Features
- `codebase-sync` 스킬 추가 — 코드베이스 현재 상태를 파악하고 문서·코드 불일치를 찾아 수정한 뒤 커밋·PR까지 이어서 처리. 범위를 `docs`/`code`/전체로 지정 가능하며, 파악 결과 확인과 수정 후 커밋 전 2단계 [STOP]으로 범위 초과 수정을 방지 ([`ffebc8f`])

---

## [common/0.11.0] — 2026-06-22

### ✨ New Features
- `skill-metrics` 스킬 추가 — Claude Code 세션 JSONL을 집계해 스킬/워크플로우 사용을 정량 지표로 환산. ① AutoScore(자동화 우선순위 = 주간호출 × (평균후속체인+1) × (1+마찰율))로 무엇을 먼저 자동화할지 산정하고, ③ Reach(도달률·빈도·일별분포)로 채택 추이를 추적. 미사용 세션을 거시적 미활용 신호로 본다(작업별 미활용은 수동 매핑 부담으로 제외). 측정 코어는 `scripts/measure.py`에 위임해 토큰을 아낀다 ([`ef7a81d`])
- `finish` 스킬 추가 — 작업 끝의 `정리→리뷰→커밋→push→PR` 체인을 한 호출로 오케스트레이션. 커밋/push 스킬을 하드코딩하지 않고 프로젝트 CLAUDE.md 규칙으로 감지하며(가용성 확인 후 없으면 `common:commit`/`git push`로 폴백), code-review effort를 유효값으로 정규화하고 push 전 사용자 확인 게이트를 둔다 ([`39b12f6`])

---

## [common/0.10.0] — 2026-06-16

### ✨ New Features
- `memory-curator` 스킬 추가 — 세션 JSONL에서 메모리 후보를 추출·저장하는 기본 모드와, 누적 메모리를 정리(중복·상충·만료 식별, CLAUDE.md 승격·문서화 후보 제안)하는 리뷰 모드 2종. 중복 방지 필터(코드·git·PR·기존 메모리·CLAUDE.md에 이미 있으면 거름)를 메모리 비대화를 막는 단일 관문으로 둠 ([`ca63889`], [`21f3486`])

### ♻️ Refactoring
- `retrospective` 메모리 처리를 `memory-curator`에 위임 — 회고는 메모리 "후보"만 식별하고 저장·중복판정·MEMORY.md 인덱스 검증은 memory-curator 단일 관문에 일임해 두 스킬이 같은 세션을 중복 수집하지 않게 분리. 함께 신규 스킬 추천·문서화 공백 카테고리를 추가하고, CLAUDE.md 반영을 전역/프로젝트/디렉토리/로컬(`CLAUDE.local.md`) 4계층으로 분류 ([`ca63889`])

---

## [common/0.9.0] — 2026-06-16

### ♻️ Refactoring (Breaking)
- 노션 의존 스킬 생태계를 로컬 .md 기반으로 전면 전환 — 노션 동기화 부담·env(DS_ID) 셋업 피로·구현계획서 일회성을 이유로 워크플로우 DB 의존을 폐지. `notion-context`·`notion-knowledge`·`notion-doctor` 3개 스킬 삭제, `notion-report` → `report` 리네임 + 저장을 Notion API에서 프로젝트 `private/<유형>-<slug>-<날짜>.md`로 전환(렌더 문법 변환·DS_ID·옵션 등록 제거, 노션 MCP 3개 대신 Write 추가, YAML 프론트매터 도입). 구현계획 유형은 `report`에서 제거해 `draft-plan`으로 일원화 ([`6e12499`], [`c21eead`])

### ♻️ Refactoring
- `draft-plan`을 커스텀 플랜 모드로 재정의 — Step 5의 노션 저장(`notion-report` 위임)을 `private/plan-<slug>-<날짜>.md` 직접 Write로 교체, allowed-tools에 Write 추가(Edit는 제외해 코드 수정 불가 유지), 기본 Plan 모드(`EnterPlanMode`/`ExitPlanMode`)와의 관계 및 피드백 흐름(노션 댓글 → 대화)을 명시 ([`ff5b535`])
- `apply-review` 보고서 저장을 로컬 전용으로 환원 — 노션 우선 저장과 노션 MCP 3개를 제거하고 `private/analysis-pr{N}-<날짜>.md`로 통일(Write 추가, `report`와 프론트매터 컨벤션 공유). `retrospective`의 범위 확장 옵션에서 사용 불가가 된 '노션 미팅 노트' 항목 제거 ([`adea035`])
- `draft-plan` 코드 리뷰 단계에 `/simplify` 선행 추가 — `/code-review`(버그 검출) 전에 `/simplify`(재사용·단순화·효율 정리)를 먼저 실행하도록 골격·작성 가이드에 명시. code-review 항목은 단순 정리·효율의 중복 반영을 배제 ([`a1b5626`])

---

## [common/0.8.7] — 2026-06-15

### ♻️ Refactoring
- `create-ppt` 스크립트를 컴포넌트 조립 방식으로 전면 재설계 — 기존 단일 파일에 18장 순서를 하드코딩하던 구조를 `scripts/components/` 디렉터리에 16개 슬라이드 컴포넌트로 분리. 각 컴포넌트는 `render(slide, ctx) → str` 계약을 구현하고, `generate_ppt.py`는 JSON의 `slides` 배열을 순회하며 해당 컴포넌트를 호출하는 조립기 역할만 수행. `slides` 미지정 시 기존 18장 DEFAULT_PRESET을 자동 사용해 회귀 없음. 배지 번호·섹션 번호·목차는 조립 시점 `ctx`에서 동적 계산되어 하드코딩 완전 제거. SKILL.md를 컴포넌트 카탈로그 + `slides` 인라인 JSON 방식으로 전면 갱신 ([`aad11a7`])

---

## [common/0.8.6] — 2026-06-15

### ♻️ Refactoring
- `draft-plan` 계획서 구조를 "리빙 문서"로 재편 — 0.8.2에서 도입한 목표·달성기준·성공기준·검증 4층의 *구분*은 유지하되, 달성기준·성공기준·검증을 별도 섹션으로 반복 나열하지 않고 **추적 매트릭스 한 표의 열**(달성기준↔성공기준↔검증↔현황)로 묶어 중복을 제거. 계획(목표값)과 진행 현황(실측값)을 2부로 분리하고, `## 진행 현황`(생성 시 빈 스캐폴드)·`## 변경·결정 로그`(생성 결정 시드, append-only)를 추가. 변동 값은 현황/로그 한 곳에만 두는 단일 출처 규칙을 명시 ([`abf262c`])

### ✨ New Features
- `notion-report`에 Notion 렌더 문법 규칙 추가 — 파이프 마크다운 표는 렌더되지 않으므로 `<table>` HTML로, 요약/상태 콜아웃은 `<callout>`로 변환해 저장하도록 명시(코드블록 밖 `~`·`<`·`>` 이스케이프 포함). `구현계획` 유형을 리빙 문서 구조로 안내하고, 기존 보고서의 진행현황·로그 갱신은 `notion-update-page`로 별도 처리함을 경계로 명시 ([`abf262c`])

---

## [common/0.8.5] — 2026-06-15

### ✨ New Features
- `notion-report` 보고서 작성 원칙에 코드 발췌·자립 구성 규칙 추가 — 코드를 다루는 보고서(분석·완료보고·구현계획)는 `경로:라인` 줄번호 나열을 금지하고 핵심 코드를 발췌해 코드블록으로 설명하도록 변경. 보고서만 읽어도 ① 배경 ② 문제(발췌로 증명) ③ 하고자 하는 것을 파악할 수 있게 자립적으로 구성하도록 명시 (`draft-plan` 원칙과 동일 기조) ([`96aa309`])

---

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
