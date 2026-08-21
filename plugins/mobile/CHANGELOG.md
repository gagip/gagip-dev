# Changelog — mobile

## [0.2.4] - 2026-08-21

### Removed
- **android-review**: 스킬을 제거했다. 플랫폼 특화 리뷰 지침은 마켓플레이스가 아니라 대상 레포의 CLAUDE.md나 레포 전용 스킬에 있어야 한다고 판단했다. 함께 있던 안드로이드 특화 문서(`kotlin-conventions`·`compose-patterns`·`service-guidelines`)도 같이 제거했으며, 필요하면 이 커밋 이전 이력에서 꺼내 대상 레포로 옮긴다. 언어 무관 철학 문서는 `common:coding-philosophy`로 승격했고 범용 리뷰는 `common:module-review`가 담당한다 (`c436117`)

## [0.2.3] - 2026-08-18

### Fixed
- **android-review**: `references/` 문서가 리뷰 대상 레포의 규칙이 아니라 특정 참고 프로젝트의 관례(또는 개인 철학)라는 점을 명시하고, 인용 전에 그 규칙이 리뷰 대상 레포에도 적용되는지 판단하는 절차를 추가했다 (`010c2bb`)

## [0.1.0] - 2026-06-30

### Added
- 신규 플러그인 `mobile` — 모바일 앱(Android/iOS) 크로스 플랫폼 품질 검토 도메인
- `review-quality` 스킬 — 플랫폼 공식 품질 기준 기반 정적 검토(진단 전용)
  - 스택 자동 감지(Android/iOS 네이티브 + RN/Flutter/Tauri/Capacitor) 후 해당 플랫폼 항목만 점검
  - 지적마다 Android Core App Quality 항목 / Apple ARG·HIG 조항 근거 인용
  - 확정 / 의심 / 확인 불가(런타임) 3단계 강도 구분
- 자산: `references/quality-map.md`(Android↔Apple 1:1 매핑 표), `references/detection-hints.md`(스택 감지 + 점검 단서)
- 실제 사내 모바일 앱 검증 후 반영: 모노레포 비대화형 폴백, 공개 클라이언트 시크릿 항목(SEC-22) 신설, Android `allowBackup`·iOS 릴리스 엔타이틀먼트(`aps-environment`) 점검 단서, 하이브리드 터치영역/대비를 런타임 측정으로 분류
