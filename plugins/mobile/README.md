# mobile

모바일 앱(Android/iOS) 플랫폼 품질 검토 도구. `android`/`tauri` 플러그인이 단일 플랫폼에
특화된 것과 달리, 이 플러그인은 **Android·iOS 양 플랫폼의 출시 품질 기준을 교차로 보는**
크로스 플랫폼 도메인을 담는다.

## 스킬

### `review-quality`

모바일 앱 코드베이스를 플랫폼 공식 품질 기준에 비춰 정적 검토하고, 위반·미흡 항목을 근거와
함께 리포트한다(진단 전용, 코드 수정 안 함).

- **판단 기준**: Android Core App Quality + Apple App Review Guidelines(ARG)/HIG
- **동작**: 스택 자동 감지 → 해당 플랫폼 항목만 점검 → 지적마다 기준 근거 인용
- **대상**: Android·iOS 네이티브 + React Native·Flutter·Tauri·Capacitor 하이브리드
- **트리거 예**: "출시 전 품질 점검", "스토어 심사 전 확인", "권한/네트워크 보안 점검", "접근성/다크모드 점검"

#### 자산 (`references/`)

- `quality-map.md` — Android 품질 항목 ↔ Apple 대응(ARG/HIG/프레임워크) 1:1 매핑 표 (근거 인용용)
- `detection-hints.md` — 스택 감지 신호 + 플랫폼별 코드 점검 단서(grep 패턴·파일 위치)

## 출처

- Android Core App Quality — https://developer.android.com/docs/quality-guidelines/core-app-quality
- Apple App Review Guidelines — https://developer.apple.com/app-store/review/guidelines/
- Apple Human Interface Guidelines — https://developer.apple.com/design/human-interface-guidelines/
