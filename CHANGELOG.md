# CHANGELOG

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
