# Changelog — android

## [0.3.0] - 2026-03-17

### Added
- `review-code`: Service 리뷰 가이드라인 추가 (`references/android/service-guidelines.md`)
  - 서비스 타입 선택 기준 (Foreground Service / WorkManager / 코루틴)
  - Foreground Service — Manifest 선언, foregroundServiceType, startForeground() 타이밍
  - onStartCommand() 반환값, 생명주기 리소스 정리, 권한/버전별 제약
  - Bound Service 바인딩 생명주기
  - Service ↔ Compose 통신 (StateFlow, DisposableEffect)
- `review-code`: 아키텍처 체크리스트에 references 링크 명시

## [0.2.0] - 이전 릴리즈

- 스킬 allowed-tools 필드 추가
- Compose nullable state 처리 패턴 추가
