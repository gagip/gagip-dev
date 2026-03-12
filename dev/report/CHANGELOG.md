# Changelog

## [0.2.0] - 2026-03-13

### common

#### Fixed
- `validate_commit`: 커밋 완료 후 경고(PostToolUse) → 커밋 전 차단(PreToolUse)으로 전환
- `hooks.json`: 중복 `PostToolUse` 제거, `PreToolUse`로 통합
- `block_sensitive_files`: `.env` 패턴을 열거 방식에서 `startswith(".env")`로 강화 (`.env.staging` 등 변형 포괄)

#### Added
- `skill-consistency-reviewer` 에이전트 추가 — 스킬 간 일관성 일괄 점검
- `apply-review`, `commit`, `create-issue`, `create-pr`: `## 행동 원칙` 섹션 추가
- `implement`, `create-issue`: `argument-hint` frontmatter 추가
- `write-report`: `user-invocable: false` 설정 (AI 전용 스킬로 전환)

#### Changed
- `implement`: `[STOP × N]` → `[STOP]` 표기 통일
- `write-report`: `## 원칙` → `## 행동 원칙` 섹션명 통일
- `skill-consistency-reviewer`: `plugins/*/skills/*/SKILL.md` 탐색 경로 추가

### android

#### Added
- `review-code`: 행동 원칙 산문 → `[STOP]` 태그 명시

---

## [0.1.0] - 초기 릴리즈

- common 플러그인 초기 구성 (commit, create-issue, create-pr, apply-review, implement, changelog, validate-skill, write-report)
- android 플러그인 초기 구성 (architect, review-code, write-test)
- 훅 초기 구성 (block_sensitive_files, validate_commit)
