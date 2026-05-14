# 디버깅 가이드라인

## Tauri 모바일에서 멀티 레이어 Breakpoint가 어려운 이유

Flutter, React Native와 달리 Tauri는 런타임이 세 개가 얽혀 있어 하나의 IDE에서
전 레이어를 동시에 breakpoint로 잡는 것이 구조적으로 어렵다.

```
Android Studio
  └─ JVM (Kotlin)   → attach 가능
       └─ Rust       → attach 까다로움
            └─ WebView → Chrome DevTools로 별도 연결
```

**결론: Tauri 모바일에서 멀티 레이어 디버깅은 로그가 주력이다.**

## 레이어별 디버깅 도구

| 레이어 | 도구 | 비고 |
|--------|------|------|
| React | Chrome DevTools (`chrome://inspect`) | Breakpoint 가능 |
| Rust | `tauri-plugin-log` → Logcat | Breakpoint 사실상 불가 |
| Kotlin | Android Studio / `Log.d` → Logcat | Breakpoint 가능 |
| 레이어 간 흐름 | 브리지 경계 체크포인트 로그 | 로그가 유일한 수단 |

## 브리지 경계 체크포인트

레이어 간 경계마다 로그를 찍어 어느 레이어에서 문제가 생겼는지 빠르게 좁힌다.

```
[Native]  데이터 수집 완료, 전송 시작  → Log.d / os_log
[Rust]    Native에서 수신              → log::debug!
[Rust]    React로 emit                 → log::debug!
[React]   emit 수신                    → console.info
```

## 로그 작성 원칙

지금 단계에서는 형식보다 **습관**이 더 중요하다.
불편함이 생길 때 형식을 개선하는 방식으로 자연스럽게 수렴한다.

- **어디서, 무슨 값인지** 메시지에 담는다
- 태그는 모듈명/클래스명을 활용해 수동 타이핑을 피한다
- 민감 데이터(파형 값, 개인정보 등)는 메타데이터만 찍는다

```rust
// 나쁜 예
log::error!("error occurred");

// 좋은 예 — 위치 + 값 + 상황
log::error!("emit failed: count={}, rate={}", 
    payload.samples.len(), payload.sampling_rate);
```

```rust
// 민감 데이터 — 원시값 전체 노출 금지
log::debug!("data: {:?}", payload.raw_values);  // 나쁜 예

// 메타데이터만
log::debug!("data: count={}, first={:.3}, last={:.3}",
    payload.raw_values.len(),
    payload.raw_values.first().unwrap_or(&0.0),
    payload.raw_values.last().unwrap_or(&0.0)
);
```

## tauri-plugin-log 설정

Rust 로그는 브리지 중간에 위치해 가장 중요한 레이어다. 모든 환경에서 볼 수 있도록 타겟을 명시적으로 설정한다.

```rust
// src-tauri/src/main.rs
tauri::Builder::default()
    .plugin(
        tauri_plugin_log::Builder::new()
            .level(log::LevelFilter::Debug)  // 개발
            // .level(log::LevelFilter::Info) // 릴리즈
            .targets([
                Target::new(TargetKind::Stdout),   // tauri dev 터미널
                Target::new(TargetKind::Logcat),   // Android Logcat
                Target::new(TargetKind::Webview),  // Chrome DevTools Console
            ])
            .build()
    )
```

Webview 타겟 덕분에 Rust 로그가 Chrome DevTools에서 React 로그와 함께 보인다.
Kotlin 로그는 Tauri 로그 시스템과 별개라 Logcat에서만 확인 가능하다.

## 로그 뷰어

| 실행 환경 | Rust 로그 | Kotlin 로그 | React 로그 |
|-----------|----------|------------|-----------|
| `tauri dev` (터미널) | 터미널 stdout | - | Chrome DevTools |
| Android 디바이스/에뮬레이터 | Logcat + Chrome DevTools | Logcat | Chrome DevTools |
| iOS 디바이스/시뮬레이터 | Console.app | Console.app | Chrome DevTools |

## 개발 환경별 권장 뷰어

```
tauri dev        → 터미널 (Rust) + Chrome DevTools (React)
Android 디버깅   → Chrome DevTools (Rust + React) + Logcat (Kotlin)
iOS 디버깅       → Console.app (Rust + Swift) + Chrome DevTools (React)
```

## Logcat 필터링

```bash
adb logcat -s RustStdoutStderr          # Rust 로그만
adb logcat -s MyBridgeTag               # 특정 Kotlin 태그만
adb logcat -s RustStdoutStderr -s MyBridgeTag  # 둘 다
```
