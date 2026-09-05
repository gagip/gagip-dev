# CHANGELOG

## [0.3.3] - 2026-09-05

### 🐛 Fix
- **commit**: 커밋 스킬에서 push 정책을 제거했다. 커밋 스킬은 커밋까지만 담당하고 push 여부는 호출한 세션의 CLAUDE.md 규칙을 따르도록 했다 (`0b71d9b`)

## [0.3.2] - 2026-09-02

### 🐛 Fix
- **report-issue**: 배포되지 않는 스킬 참조를 제거했다. 브랜치 생성이 목적일 때 다른 스킬로 넘기라는 안내가 로컬 전용 스킬을 가리키고 있어 삭제했다 (`b949992`)

## [0.3.1] - 2026-09-01

### ✨ Feat
- **commit**: `common:build-skill` 러너용 결정론적 테스트 케이스(`evals/commit-basic.py`)를 추가했다. `PROMPT` 상수 + `check(ctx)` 함수 형식으로, commit 스킬 발동·커밋 수·메시지 포맷·working tree clean·`git add`→`git commit` 순서·`git push` 미실행을 Python `assert`로 검증한다 (`ca4e44c`)

## [0.3.0] - 2026-08-27

### ✨ Feat
- **commit/create-pr**: `claude plugin eval` 케이스(commit-basic, create-pr-stop-gate)를 추가해 커밋 메시지 포맷·PR 생성 STOP 게이트 준수 여부를 검증할 수 있게 했다 (`6b887e2`)

### ♻️ Refactor
- **coding-philosophy/module-review**: `apply-review`를 제거하고 `coding-philosophy`를 `module-review`의 참조 문서로 강등했다 (`7a2428d`)

## [0.2.1] - 2026-08-26

### ♻️ Refactor
- **worktree-scaffold**: 90일 세션 로그 집계 결과 호출 이력이 0건으로 확인돼 제거했다. development README 스킬 목록과 루트 README 스킬 카운트도 함께 갱신했다 (`8d44fcc`, `242e6f9`)

## [0.2.0] - 2026-08-26

### ✨ Feat
- **coding-philosophy/module-review**: `common`에서 편입해 코드 품질 판정 기준·모듈 구조 리뷰 스킬을 추가했다. 이름도 `git-workflow`에서 `development`로 개명했다 (`040b905`)

## [0.1.0] - 2026-08-26

### ✨ Feat
- **apply-review/commit/create-pr/report-issue/worktree-scaffold**: `common`에서 git/GitHub 작업 흐름 스킬 5개를 분리해 신설. 각 스킬의 이전 이력은 `plugins/common/CHANGELOG.md`에 남아 있다
