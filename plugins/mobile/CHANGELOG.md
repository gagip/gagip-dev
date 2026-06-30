# Changelog — mobile

## [0.1.0] - 2026-06-30

### Added
- 신규 플러그인 `mobile` — 모바일 앱(Android/iOS) 크로스 플랫폼 품질 검토 도메인
- `review-quality` 스킬 — 플랫폼 공식 품질 기준 기반 정적 검토(진단 전용)
  - 스택 자동 감지(Android/iOS 네이티브 + RN/Flutter/Tauri/Capacitor) 후 해당 플랫폼 항목만 점검
  - 지적마다 Android Core App Quality 항목 / Apple ARG·HIG 조항 근거 인용
  - 확정 / 의심 / 확인 불가(런타임) 3단계 강도 구분
- 자산: `references/quality-map.md`(Android↔Apple 1:1 매핑 표), `references/detection-hints.md`(스택 감지 + 점검 단서)
- 실제 레포(voltera-app-rn) 검증 후 반영: 모노레포 비대화형 폴백, 공개 클라이언트 시크릿 항목(SEC-22) 신설, Android `allowBackup`·iOS 릴리스 엔타이틀먼트(`aps-environment`) 점검 단서, 하이브리드 터치영역/대비를 런타임 측정으로 분류
