# 계약 프로그래밍 가이드라인

## 기본 원칙

계약 프로그래밍의 철학은 레이어 전체에 공통이지만, **표현 방식은 언어마다 다르다.**
타입 시스템으로 표현할 수 있는 것은 타입으로, 그렇지 않은 것만 런타임 검증으로 처리한다.

| 레이어 | 관용적 방식 | 비고 |
|--------|-----------|------|
| Kotlin | `require()` / `check()` | 값 범위를 타입으로 표현하기 번거로움 |
| Rust | 타입 + `Result` | 타입으로 표현하는 게 자연스러움 |
| React/TS | 타입 가드 + 방어적 렌더링 | 컴파일 타임 타입이 대부분 커버 |

## 브리지 경계와 타입 보장

브리지를 넘는 순간 직렬화/역직렬화가 일어나 TypeScript 타입 보장이 사라진다.

```
Native (플랫폼 타입)
    ↓  JSON 직렬화
Rust (serde 역직렬화)
    ↓  JSON 직렬화
React (TypeScript)   ← 런타임 타입 보장 없음
```

각 레이어는 타입을 독립적으로 정의해야 한다.

## Single Source of Truth — Rust

세밀한 계약 조건은 **Rust 한 곳에만** 정의한다.
Kotlin/Swift는 명백한 오류만 차단하고 세밀한 범위 검증은 Rust에 위임한다.
변경 시 Rust만 수정하면 영향 범위가 최소화된다.

```rust
// src/contract.rs — 계약 상수 한 곳에 모음
pub const RATE_MIN: f32 = 490.0;
pub const RATE_MAX: f32 = 520.0;
pub const VALUES_MAX_LEN: usize = 15_000;
pub const ID_MIN: i64 = 0;
```

## 레이어별 구현

### Kotlin — 명백한 오류만

```kotlin
fun sendPayload(values: List<Float>, rate: Int, id: Long) {
    require(values.isNotEmpty()) { "values is empty" }
    require(id >= 0) { "id must not be negative" }
    // rate 범위는 Rust에 위임

    Log.d(TAG, "sending count=${values.size} rate=${rate}Hz")
    transmitToRust(values, rate, id)
}
```

### Rust — 진짜 계약 검증

```rust
// src/domain.rs
impl TryFrom<RawPayload> for ValidatedPayload {
    type Error = DomainError;

    fn try_from(p: RawPayload) -> Result<Self, Self::Error> {
        if p.values.is_empty() {
            return Err(DomainError::EmptyValues);
        }
        if p.values.len() > VALUES_MAX_LEN {
            return Err(DomainError::TooManyValues(p.values.len()));
        }
        if !(RATE_MIN..=RATE_MAX).contains(&p.rate) {
            return Err(DomainError::InvalidRate(p.rate));
        }
        if p.id < ID_MIN {
            return Err(DomainError::InvalidId(p.id));
        }
        Ok(Self { /* ... */ })
    }
}

#[tauri::command]
fn receive_payload(payload: RawPayload, app: AppHandle) -> Result<(), String> {
    let validated = ValidatedPayload::try_from(payload)
        .map_err(|e| e.to_string())?;

    log::debug!("received count={} rate={}Hz",
        validated.values.len(),
        validated.rate
    );

    app.emit("data-event", &validated).map_err(|e| e.to_string())?;
    Ok(())
}
```

### React — Rust 신뢰 + 방어적 렌더링

Rust에서 검증을 통과한 데이터만 emit되므로 타입 캐스팅으로 충분하다.
타입 가드보다 방어적 렌더링에 집중한다.

```typescript
// 브리지 수신 — Rust 신뢰
listen('data-event', (event) => {
    const payload = event.payload as DevicePayload;
    useDataStore.getState().setPayload(payload);
});

// 컴포넌트 — 방어적 렌더링 (검증이 아닌 UX 목적)
export function DataViewer() {
    const payload = useDataStore((s) => s.payload);

    if (!payload) return <EmptyState message="데이터를 기다리는 중..." />;

    return (
        <View>
            <DataChart values={payload.values} rate={payload.rate} />
        </View>
    );
}
```

## 계약과 로그의 관계

계약 프로그래밍과 로그는 보완 관계다.

```
계약으로 경계를 명확히 하고
로그로 어디서 깨졌는지 추적한다
```

계약 위반 시 반드시 로그를 함께 남긴다.

```rust
if p.values.is_empty() {
    log::error!("contract violated: values is empty");
    return Err(DomainError::EmptyValues);
}
```

## 전체 흐름 요약

```
Kotlin/Swift  명백한 오류만 차단 (변경 거의 없음)
      ↓
Rust          진짜 계약 정의 및 검증 (Single Source of Truth)
      ↓
React         Rust 신뢰 + 방어적 렌더링
```
