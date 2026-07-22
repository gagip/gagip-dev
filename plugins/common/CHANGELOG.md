# CHANGELOG

## [0.19.0] - 2026-07-22

### ✨ Feat
- **draft-plan**: 계획서 골격에 `예상 결과 (산출물 미리보기)` 권장 섹션 추가 — 산출물 폴더 구조·출력 형식 예시·기대효과·리스크를 구현 전에 보여 판단을 돕는다("해당 시" 권장, 채운 값은 예시임을 명시)

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
