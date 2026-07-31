# CHANGELOG

## [0.19.7] - 2026-07-31

### 🐛 Fix
- **draft-plan**: 코드 리뷰 체크리스트에서 신뢰할 수 없던 `/code-review medium` 항목을 제거하고, `hunk-pr-review`를 무조건이 아니라 리뷰 과정에서 사용자 결정·확인이 필요한 지점이 남았을 때만 조건부로 제안하도록 바꿨다 (`7e0463a`)

## [0.19.6] - 2026-07-29

### 🐛 Fix
- **draft-plan**: `/code-review`가 일부 모델·환경에서 Skill 도구로 호출되지 않을 수 있다는 캐비어트를 코드 리뷰 체크리스트에 추가했다(voltera-app-rn 이슈 #179 구현 중 실제로 이 에러로 막혔던 경험 반영, 확정된 사실 아님을 명시) (`ff642ed`)

## [0.19.5] - 2026-07-28

### ♻️ Refactor
- **draft-plan**: 자체 플랜 모드(계획·구현 세션 분리, `private/` 저장)를 내장 Plan Mode(`EnterPlanMode`/`ExitPlanMode`) 애드온으로 전환했다. `ExitPlanMode` 승인 직후 같은 세션에서 바로 구현으로 이어가며, 계획 파일은 하네스 지정 경로(`~/.claude/plans/`)에 작성한다 (`c9dd256`)

## [0.19.4] - 2026-07-28

### 🐛 Fix
- **create-pr**: PR 기본 생성 모드를 draft에서 ready로 변경했다. 사용자가 명시적으로 draft를 요청한 경우에만 `--draft` 옵션을 추가한다 (`ded24d8`)

## [0.19.3] - 2026-07-28

### 🐛 Fix
- PreToolUse 훅(`block_sensitive_files.py`, `validate_commit.py`) 제거. python이 설치되지 않은 환경에서 `python: command not found`로 Edit/Write/Bash 도구 호출마다 훅 오류가 발생했다 (`f4dfa32`)

## [0.19.2] - 2026-07-28

### 🐛 Fix
- **finish**: PR 단계(Step 5)가 `create-pr`을 하드코딩하고 있어, 같은 문서의 커밋 단계(Step 3)·설계 원칙("커밋·PR 스킬은 프로젝트 규칙을 따른다")과 어긋났다. 이제 Step 3과 같은 우선순위로 PR 스킬을 감지한다 — 가까운 `CLAUDE.md` → 전역 `CLAUDE.md` → `common:create-pr` 폴백. 폴백까지 없거나 비활성화된 경우엔 `gh pr create`를 직접 실행하지 않고 사용자에게 확인한다(base 판정·중복 PR 확인 같은 안전 검사를 건너뛰지 않기 위함) (`190ea3e`)

## [0.19.1] - 2026-07-27

### 🐛 Fix
- **draft-plan**: 선행 검증을 커밋에서 분리했다. 같은 절이 "본 구현이 아닌 **버리는 최소 코드**"라고 하면서 그 검증을 "커밋 0(게이트)"로 부르고 있어, 버릴 코드를 커밋하는 것처럼 읽혔다. 이제 검증 코드는 커밋하지 않고 버리며, 검증으로 알게 된 것을 계획서 본문·변경 로그에 반영해 계획을 고친 뒤 본 작업 첫 커밋부터 시작한다. 함께 착수 재판단 항목을 추가했다 — 한 점만 찔렀는데 본 구현이 낼 결과의 상당 부분이 그 자리에서 나오는 경우가 있어, 본 구현으로 **새로 얻는 것이 얼마나 남는지** 보고 얇으면 범위를 줄이거나 접는다(게이트 통과는 "기술적으로 된다"이지 "만들 값어치가 있다"가 아니다) (`0d87c15`)

## [0.19.0] - 2026-07-22

### ✨ Feat
- **draft-plan**: 계획서 골격에 `예상 결과 (산출물 미리보기)` 권장 섹션 추가 — 산출물 폴더 구조·출력 형식 예시·기대효과·리스크를 구현 전에 보여 판단을 돕는다("해당 시" 권장, 채운 값은 예시임을 명시) (`dccc9a7`)

> 0.9.0–0.18.2 구간은 CHANGELOG 미기록 (릴리즈 이력은 git log 참조). 0.19.0부터 기록 재개.

## [0.8.0] - 2026-06-10

### ✨ Feat
- **notion-doctor**: Notion 워크플로우 셋업(env·DB 스키마·볼트 폴백 경로) 점검·구성 스킬 추가

### ♻️ Refactor
- **draft-plan**: 옛 `private/plans/` 로컬 저장 잔재를 Notion Reports DB 위임으로 정정
- **notion-knowledge**: 볼트 폴백 경로를 `$HOME/personal/gagip-obsidian/wiki/`로 수정(깨진 외장 경로 제거), 위치 문구를 회사 워크스페이스로 갱신
- **notion-context**: 위치 문구를 회사 워크스페이스로 갱신

## [0.6.0] - 2026-06-01

### ✨ Feat
- **draft-plan**: 구현 계획서 작성 스킬 추가 — GitHub 이슈 또는 자연어 주제 기반, private/plans/ 로컬 저장
- **report-issue**: GitHub 이슈 생성 스킬 추가 — 자연어로 버그/기능 요청/개선 이슈 초안 작성 및 생성
- **retrospective**: 세션 회고 스킬 추가 — 인사이트·피드백 추출 후 스킬/메모리/볼트에 반영
- **apply-review**: 리뷰 코멘트 분석 보고서 생성 및 코드 수정 플로우 개선

## [0.5.1] - 2026-04-19

### ♻️ Refactor
- **apply-review**: 인터랙티브 코멘트 선택 방식 제거, 전체 분석 보고서(마크다운 파일) 저장 방식으로 개편
  - 보고서 형식에 배경/문제코드/원인분석/수정전후코드/기대효과 섹션 추가
  - 논의 완료 후 에이전트 자율 실행(수정 → 검증 → 커밋) 흐름으로 변경
- **setup-skills**: SKILL.md 수정 및 미사용 architecture.md 삭제

### ✨ Feat
- **모든 스킬**: `argument-hint` frontmatter 필드 추가 (apply-review, commit, create-pr, setup-skills)

## [0.5.0] — 2026-03-23

### ✨ New Features
- create-pr 스킬: PR을 기본 draft로 생성하도록 변경 (`44ad9aa`)
- create-pr 스킬: PR 업데이트 시 draft/ready 상태 유지 및 기존 본문 기반 수정 원칙 추가 (`44ad9aa`)

### 📝 Documentation
- README 스킬 목록을 실제 구성과 일치하도록 수정 (`7c388a7`)

## [0.3.0] — 2026-03-18

### ✨ New Features
- implement 스킬에 문제 정의 단계 추가: AI가 코드베이스를 탐색한 뒤 사용자와 함께 현재 상태·목표 상태·범위를 합의하는 0단계 추가 (`69b4b6c`)
- plugin-commit 스킬 추가: 변경 파일 경로로 scope를 자동 감지하여 이 프로젝트 커밋 컨벤션에 맞는 커밋을 수행하는 스킬 (`397939c`)
- release 스킬: plugins 외부 변경사항 무시 규칙 추가 (`cc120da`)
- release 스킬: 커밋 이력 분석으로 버전 유형 자동 판단 후 사용자 확인 단계 추가 (`1253e8f`)

### 📝 Documentation
- common 플러그인 README 추가 (`ac3abc4`)
