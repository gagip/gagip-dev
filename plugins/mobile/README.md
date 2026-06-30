# mobile

모바일 제품 개발(Android/iOS/Tauri) 전반을 아우르는 플러그인.
코드 리뷰·테스트 작성부터 출시 품질 검토·아키텍처 가이드라인까지 하나의 플러그인에서 다룬다.

## 스킬

### `android-review`

Android 코드베이스 리뷰. 가독성·정확성·보안·아키텍처·테스트를 점검한다.

- **동작**: 인자 없으면 `git diff HEAD` 기준, 인자 있으면 지정 경로 기준
- **참조**: Kotlin 컨벤션, Compose 패턴, Service 가이드라인, 코딩 철학 (`references/android/`, `references/common/`)
- **트리거 예**: "리뷰해줘", "코드 봐줘", "PR 리뷰", "변경사항 확인"

### `android-test`

Android 테스트 코드 작성. 대상 코드 분석 → 시나리오 논의 → 테스트 계획 → 코드 생성 순으로 진행한다.

- **참조**: `references/android-test-guidelines.md` (BehaviorSpec, Fake/Mock 전략, StateFlow 검증)
- **트리거 예**: "테스트 써줘", "테스트 만들어줘", "단위 테스트 추가"

### `tauri-guideline`

Tauri v2 모바일 프로젝트(Native↔Rust↔React 3-레이어 브리지)의 아키텍처·디버깅·테스트·플러그인 선택·계약 프로그래밍 가이드라인을 제공한다.

- **참조**: `references/` 하위 architecture, debugging, testing, contracts, plugins-catalog
- **트리거 예**: "tauri 구조", "레이어 분리", "브리지 디버깅", "tauri 플러그인 골라줘"

### `review-quality`

모바일 앱 코드베이스를 플랫폼 공식 품질 기준에 비춰 정적 검토하고, 위반·미흡 항목을 근거와 함께 리포트한다 (진단 전용, 코드 수정 안 함).

- **판단 기준**: Android Core App Quality + Apple App Review Guidelines(ARG)/HIG
- **동작**: 스택 자동 감지 → 해당 플랫폼 항목만 점검 → 지적마다 기준 근거 인용
- **대상**: Android·iOS 네이티브 + React Native·Flutter·Tauri·Capacitor 하이브리드
- **참조**: `references/quality-map.md` (Android↔Apple 1:1 매핑), `references/detection-hints.md` (스택 감지 단서)
- **트리거 예**: "출시 전 품질 점검", "스토어 심사 전 확인", "권한/네트워크 보안 점검"

## 출처

- Android Core App Quality — https://developer.android.com/docs/quality-guidelines/core-app-quality
- Apple App Review Guidelines — https://developer.apple.com/app-store/review/guidelines/
- Apple Human Interface Guidelines — https://developer.apple.com/design/human-interface-guidelines/
