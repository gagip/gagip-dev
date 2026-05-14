# Tauri 플러그인 선택 가이드라인

## 자제작 vs 공식 플러그인 판단 기준

| 조건 | 선택 |
|------|------|
| 플랫폼 하드웨어 SDK에 직접 의존 (Wear OS, HealthKit 등) | 자제작 플러그인 |
| 도메인 특화 로직 (데이터 검증, 브리지 프로토콜) | 자제작 플러그인 |
| 범용 OS 기능 (HTTP, 파일, 알림, 저장소 등) | 공식/커뮤니티 플러그인 |
| 보안 민감 기능 (생체인증, OAuth) | 검증된 공식 플러그인 우선 |

자제작 플러그인은 `tauri-plugin-<domain>-<function>` 형태로 이름을 짓는다.

## 공식/커뮤니티 플러그인 목록

### 필수 (출시 전 완료)

| 플러그인 | 용도 | 비고 |
|---|---|---|
| `tauri-plugin-http` | 서버 API 통신 | fetch 대신 사용, CORS 우회 |
| `tauri-plugin-sql` | 로컬 데이터 캐싱 | SQLite 기반, 측정 이력·분석 결과 |
| `tauri-plugin-store` | 경량 키-값 저장 | 인증 토큰, 사용자 설정 |
| `tauri-plugin-log` | Rust 레이어 로그 | Stdout/Logcat/Webview 동시 타겟 |

### 출시 전 (기능 완성도)

| 플러그인 | 용도 | 비고 |
|---|---|---|
| `tauri-plugin-biometric` | 지문 / Face ID 인증 | 민감 데이터 접근 보호 |
| `tauri-plugin-notification` | 푸시/로컬 알림 | 분석 완료, 리마인더 |
| `tauri-plugin-deep-link` | 앱 딥링크 처리 | OAuth 콜백, 외부 앱 연동 |
| `tauri-plugin-oauth` | 소셜 로그인 | Google, Kakao 등 |

### 출시 후 검토

| 플러그인 | 용도 | 비고 |
|---|---|---|
| `tauri-plugin-websocket` | 실시간 서버 푸시 | 분석 결과 비동기 수신 |
| `tauri-plugin-share` | 외부 공유 | 결과 PDF/이미지 공유 |
| `tauri-plugin-sentry` | 크래시 리포트 | 에러 트래킹 |
| `tauri-plugin-updater` | 앱 자동 업데이트 | 모바일은 스토어 정책 확인 필요 |
| `tauri-plugin-fs` | 파일 시스템 접근 | 내보내기, 로그 파일 |

## 플러그인 선택 시 체크 포인트

1. **플랫폼 지원 확인**: Android/iOS 모두 지원하는지 README에서 확인
2. **권한(capabilities) 비용**: 추가되는 `allowlist` 항목이 최소인지 확인
3. **공식 vs 커뮤니티**: `tauri-apps` 조직 플러그인이 우선. 커뮤니티는 마지막 커밋/이슈 활성도 확인
4. **대안 비교**: 기능이 간단하면 `invoke` + Rust 직접 구현이 더 나을 수 있음

## 플러그인 추가 절차

```toml
# src-tauri/Cargo.toml
[dependencies]
tauri-plugin-http = "2"
```

```rust
// src-tauri/src/main.rs
tauri::Builder::default()
    .plugin(tauri_plugin_http::init())
```

```json
// src-tauri/capabilities/default.json
{
  "permissions": [
    "http:default"
  ]
}
```

```typescript
// package.json (JS API가 있는 플러그인)
// npm install @tauri-apps/plugin-http
import { fetch } from '@tauri-apps/plugin-http';
```
