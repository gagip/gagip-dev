# tauri

Tauri v2 모바일 프로젝트(Native↔Rust↔React 3-레이어 브리지)의 개발 가이드라인 데이터베이스.

## 스킬

| 스킬 | 트리거 예시 |
| ---- | ----------- |
| `tauri-guideline` | "tauri 구조", "Rust랑 React 역할", "브리지 디버깅", "tauri 플러그인 골라줘", "계약 프로그래밍" |

### `tauri-guideline`

아키텍처, 디버깅, 테스트, 플러그인 선택, 계약 프로그래밍 질문에서 자동 트리거되어 일관된 가이드라인을 제공한다.
질문을 주제별로 분류한 뒤 해당 references 파일을 로드하여 원칙을 인용한다.

## 주제 인덱스

| 주제 | 파일 |
|------|------|
| 레이어 아키텍처·SSOT | `skills/tauri-guideline/references/architecture.md` |
| 디버깅·로그 | `skills/tauri-guideline/references/debugging.md` |
| 테스트 전략 | `skills/tauri-guideline/references/testing.md` |
| 계약 프로그래밍 | `skills/tauri-guideline/references/contracts.md` |
| 플러그인 선택 | `skills/tauri-guideline/references/plugins-catalog.md` |

## 적용 범위

Tauri v2 모바일 앱(Android/iOS)을 주 대상으로 한다. 데스크탑은 일부 가이드라인(디버깅, 계약 프로그래밍)이 적용되지만 모바일 특화 내용(Logcat, Product Flavor, iOS Scheme 등)은 참고 수준으로 활용한다.
