# 레이어 아키텍처 가이드라인

## 3-레이어 구조

Tauri 모바일 앱은 세 개의 독립적인 런타임이 브리지로 연결된 구조다.

```
Native (Kotlin / Swift)
  └─ Rust (Tauri core + 플러그인)
       └─ WebView (React)
```

각 레이어는 독립적인 타입 시스템을 가지며, 브리지를 넘을 때마다 JSON 직렬화/역직렬화가 일어난다.

## 레이어별 역할

| 레이어 | 역할 | 하면 안 되는 것 |
|--------|------|----------------|
| Native (Kotlin/Swift) | OS API 어댑터. 하드웨어·플랫폼 SDK 접근, OS 서비스 등록 | 도메인 로직, 세밀한 검증 |
| Rust | SSOT. 도메인 검증, 비즈니스 로직, 플랫폼 분기, 이벤트 emit | 네이티브 SDK 직접 호출 |
| React | 표현 레이어. Rust에서 받은 데이터를 렌더링 | 데이터 검증, 도메인 판단 |

**SSOT는 Rust다.** 계약 조건, 상수, 플랫폼 분기 로직은 Rust 한 곳에 정의한다.

## 데이터 흐름

### 네이티브 → React (push 방식)

```
Native (디바이스 페이로드 수집)
  └─ 직렬화 → Rust (검증 + 도메인 처리)
       └─ emit('event-name', payload) → React
```

### React → Rust (invoke 방식)

```
React (사용자 액션)
  └─ invoke('command_name', args) → Rust (처리 + 결과 반환)
       └─ 결과 → React
```

## 플랫폼 분기 원칙

React에서는 플랫폼 분기 없이 동일한 `invoke` / `listen` 호출만 사용한다.
플랫폼별 분기는 Rust 레이어에서 처리한다.

```rust
// Rust에서 플랫폼 분기 — React는 몰라도 됨
#[tauri::command]
async fn start_measurement(app: AppHandle) -> Result<(), String> {
    #[cfg(target_os = "android")]
    android_impl::start(&app)?;

    #[cfg(target_os = "ios")]
    ios_impl::start(&app)?;

    Ok(())
}
```

```typescript
// React — 플랫폼 구분 없음
await invoke('start_measurement');
```

## 타입 정의 원칙

브리지를 넘는 순간 타입 보장이 끊긴다. 각 레이어는 타입을 독립적으로 정의한다.

```
Native    — 플랫폼 네이티브 타입 (data class / struct)
    ↓ JSON
Rust      — serde 역직렬화 struct
    ↓ JSON
TypeScript — interface / type
```

JSON 필드명은 Rust의 `#[serde(rename_all = "camelCase")]`로 camelCase를 보장한다.
React 쪽 `interface`도 camelCase로 맞춘다.

```rust
#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct DevicePayload {
    sampling_rate: f32,   // → samplingRate
    lead_off: bool,       // → leadOff
}
```
