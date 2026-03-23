# CHANGELOG

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
