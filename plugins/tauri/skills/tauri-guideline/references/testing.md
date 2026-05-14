# 테스트 전략 가이드라인

## 개요

Tauri 모바일 앱은 Native → Rust → React 세 개의 레이어가 브리지로 연결된 구조다.
단위 테스트만으로는 레이어 간 문제를 잡을 수 없고, 외부 하드웨어/플랫폼 SDK 의존성 때문에 완전한 e2e 자동화에 제약이 있다.
**Mock e2e + Rust 계약 검증**을 중심으로 전략을 구성한다.

## 우선순위

| 순위 | 방식 | 도구 | 비고 |
|------|------|------|------|
| 1 | Mock e2e | Appium + 테스트 하네스 | 전체 경로 검증, CI 자동화 |
| 2 | Rust 계약 검증 | cargo test | 핵심 검증 로직, 빠른 피드백 |
| 3 | 수동 e2e | 실기기 + 실제 외부 장치 | 릴리즈 게이트 |

React/Kotlin 단위 테스트는 여유 있을 때 추가한다.

## Mock 빌드 전략

실제 하드웨어 없이 e2e를 자동화하기 위해 플랫폼별 Mock 빌드를 별도로 구성한다.
Debug 빌드는 일반 개발용으로 유지하고, Mock은 독립된 빌드 타겟으로 분리한다.

### Android — Product Flavor

```groovy
// build.gradle
android {
    flavorDimensions "env"
    productFlavors {
        mock {
            dimension "env"
            applicationIdSuffix ".mock"
        }
        real {
            dimension "env"
        }
    }
}

// 빌드 조합
// mockDebug   ← Appium CI용
// realDebug   ← 일반 개발
// realRelease ← 스토어 배포
```

```kotlin
// src/mock/DataSourceFactory.kt
class DataSourceFactory {
    fun create() = MockDataSource()
}

// src/real/DataSourceFactory.kt
class DataSourceFactory {
    fun create() = RealDataSource()
}
```

### iOS — Scheme

```
Scheme: App-Mock    → MOCK_SOURCE=1 플래그 + Debug 설정  ← Appium CI용
Scheme: App-Dev     → 일반 개발
Scheme: App-Release → 스토어 배포
```

```swift
#if MOCK_SOURCE
    MockDataSource().start()
#else
    RealDataSource().start()
#endif
```

### Rust — Feature 플래그

```toml
# Cargo.toml
[features]
mock-source = []
```

```rust
#[cfg(feature = "mock-source")]
fn data_source() -> impl DataSource {
    MockDataSource::new()
}

#[cfg(not(feature = "mock-source"))]
fn data_source() -> impl DataSource {
    RealDataSource::new()
}
```

릴리즈 빌드에 Mock 코드가 포함되지 않으므로 프로덕션에 Mock이 섞일 가능성이 없다.

## 1. Mock e2e

### Appium — 사용자 시나리오 검증

전체 경로(Native → Rust → React)를 Mock 빌드로 실행하며 UI 시나리오를 검증한다.

**커버 시나리오 예시**

```
- 앱 시작 → 외부 장치 연결 상태 표시
- 데이터 수집 시작 → 실시간 렌더링
- 오류 상태 발생 → 경고 표시
- 네트워크 없을 때 → 로컬 버퍼링 동작
```

### 테스트 하네스 — 브리지 경계 검증

Appium보다 세밀하게 브리지 경계를 제어한다.
Mock 데이터 소스에서 데이터를 주입하고 각 경계에서 올바르게 통과하는지 확인한다.

```
MockDataSource (Native)
  └─ 미리 정의된 페이로드 브로드캐스트
       └─ 실제 브리지를 타고 Rust → React로 흐름
            └─ ADB + Chrome DevTools Protocol로 결과 확인
```

**핵심 검증 항목**

- Native → Rust: 데이터가 브리지를 통과하는가
- Rust → React: JSON 필드명이 camelCase인가 (`samplingRate`, `isConnected` 등)
- React: emit된 데이터가 올바르게 렌더링되는가

camelCase 불일치는 에러 없이 조용히 `undefined`가 되므로 반드시 검증한다.

## 2. Rust 계약 검증

계약 조건은 Rust 한 곳에 정의되고(`src/contract.rs`), 검증도 Rust에서 수행한다.
`ValidatedPayload::try_from`이 핵심 테스트 대상이다.

```rust
#[cfg(test)]
mod tests {
    use super::*;

    fn valid_payload() -> RawPayload {
        RawPayload {
            values: vec![0.1, 0.2, 0.3],
            rate: 500.0,
            timestamp: 1_700_000_000,
            id: 1,
        }
    }

    #[test]
    fn valid_payload_passes() {
        assert!(ValidatedPayload::try_from(valid_payload()).is_ok());
    }

    #[test]
    fn empty_values_rejected() {
        let p = RawPayload { values: vec![], ..valid_payload() };
        assert!(matches!(
            ValidatedPayload::try_from(p),
            Err(DomainError::EmptyValues)
        ));
    }

    // 경계값 — 범위 끝단 확인
    #[test]
    fn rate_boundary() {
        let low  = RawPayload { rate: RATE_MIN, ..valid_payload() };
        let high = RawPayload { rate: RATE_MAX, ..valid_payload() };
        assert!(ValidatedPayload::try_from(low).is_ok());
        assert!(ValidatedPayload::try_from(high).is_ok());
    }
}
```

계약 조건이 바뀔 때(`contract.rs` 수정) 테스트도 함께 수정한다.

## 3. 수동 e2e (릴리즈 게이트)

자동화 e2e로 커버할 수 없는 실제 하드웨어 동작을 릴리즈 전에 직접 확인한다.

**체크리스트 템플릿**

```
[ ] 외부 장치 페어링 및 연결 상태 표시
[ ] 실제 데이터 수집 → 앱 실시간 렌더링
[ ] 오류 상태(접촉 불량 등) → 경고 표시
[ ] 네트워크 끊김 → 로컬 버퍼링 후 재전송
[ ] 백그라운드 → 포그라운드 복귀 시 상태 복원
```

## CI 파이프라인

```yaml
jobs:
  test:
    steps:
      # Rust 계약 검증 — 가장 빠름
      - name: Rust unit tests
        run: cargo test

      # Android Mock e2e
      - name: Build mock variant
        run: ./gradlew assembleMockDebug

      - name: Run Appium tests (Android)
        run: npx appium --test mockDebug

      # iOS Mock e2e
      - name: Build mock scheme
        run: xcodebuild -scheme App-Mock

      - name: Run Appium tests (iOS)
        run: npx appium --test App-Mock
```

## 자동화하지 않는 것

| 항목 | 이유 |
|------|------|
| 외부 하드웨어 SDK | 실제 기기와 장치 필요 |
| HealthKit ECG | Apple 정책상 시뮬레이터 차단 |
| Rust `log::` 호출 | 디버깅 보조 수단, 동작의 일부가 아님 |
| Kotlin `require/check` | 언어 기본 동작 수준, 테스트 가치 낮음 |
