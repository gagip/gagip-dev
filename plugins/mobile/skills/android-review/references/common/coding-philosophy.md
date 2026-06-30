# 코딩 철학 가이드라인

개인 코딩 철학. 코드 리뷰 시 이 기준으로 가독성·정확성을 평가한다.

언어에 무관하게 적용되는 원칙이며, 코드 예시는 의사코드(pseudocode) 형태로 표기한다.

의사코드의 `assert`는 릴리즈에서도 항상 활성화된 수단을 의미한다. Kotlin에서는 `require`(인자 검사)·`check`(상태 검사)가 이에 해당한다. 디버그 전용 비활성화는 원칙적으로 사용하지 않는다.

---

## 1. 계약 프로그래밍 (Contract Programming)

사전조건·불변식·사후조건을 코드로 명시한다.

| 종류 | 용도 | 실패 시 |
|------|------|---------|
| 사전조건 (Precondition) | 함수 진입 전 인자 유효성 검사 — 호출자가 잘못된 값을 전달했음을 즉시 알린다 | 인자 오류 예외 / assertion 실패 |
| 불변식 (Invariant) | 메서드 호출 전 객체 상태 유효성 검사 | 상태 오류 예외 / assertion 실패 |
| 사후조건 (Postcondition) | 함수 실행 후 반환값·상태가 약속된 범위임을 검증한다 | assertion 실패 |
| 내부 가정 검증 | 개발/디버그용 중간 검증 — 필요 시 사용 | assertion 실패 |

```
// 사전조건 — 인자 검사
function setAge(age):
    assert age >= 0 and age <= 150, "age must be in 0..150, was {age}"
    ...

// 불변식 — 상태 검사
function save():
    assert isConnected, "DB connection must be established before save()"
    ...

// 사후조건 — 반환값 검사
function average(values):
    result = sum(values) / len(values)
    assert result >= min(values) and result <= max(values), "result out of range: {result}"
    return result

// 잘못된 예 — 잘못된 입력을 조용히 보정
function setAge(age):
    age = clamp(age, 0, 150)  // 잘못된 입력을 숨김
    ...
```

**리뷰 체크포인트**
- 공개 함수 인자에 사전조건 검사가 있는가?
- 상태 의존적 메서드에 불변식 검사가 있는가?
- 반환값이 항상 유효한 범위임을 사후조건으로 보장하는가?
- 에러 메시지에 실제 값이 포함되어 있는가?

---

## 2. 빠른 실패 (Fail Fast)

잘못된 상태는 발생 즉시 감지하고 중단한다. 조용한 실패(silent failure)는 금지한다.

```
// 올바른 예 — 즉시 실패
function loadUser(id):
    assert id != "", "User ID must not be blank"
    user = repository.find(id)
    assert user != null, "User not found: {id}"
    ...

// 잘못된 예 — 조용히 넘어감
function loadUser(id):
    if id == "": return       // 왜 중단했는지 알 수 없음
    user = repository.find(id)
    if user == null: return   // 실패가 감춰짐
    ...
```

**리뷰 체크포인트**
- 비정상 상태에서 함수가 아무것도 안 하고 조용히 `return`하지 않는가?
- null/None/nil을 조용히 무시하는 패턴이 남용되지 않는가?
- 오류 메시지가 원인을 명확히 설명하는가?

---

## 3. 구조적 프로그래밍 우선 (Structured over Clever)

복잡한 함수형 체인·연산자 중첩보다 명시적인 루프와 조건문을 선호한다.

```
// 선호 — 읽기 쉬움
function findActiveItem():
    for item in items:
        if item.isActive:
            return item
    return null

// 주의 — 체인이 길어질수록 가독성이 떨어짐
function findActiveItem():
    return items
        .filter(isActive)
        .first()
        .where(createdAt > cutoff)  // 의도를 파악하기 위해 해석이 필요함
```

**리뷰 체크포인트**
- 연산자/메서드 체인이 3단계를 초과하는가?
- 콜백/람다 안에 콜백/람다가 중첩되어 있는가?
- 코드가 한 번에 이해되는가, 아니면 해석이 필요한가?

---

## 4. 에러 경계 관리 (Error Boundary)

내가 제어 가능한 범위 내에서는 예외를 생성하거나 전파하지 않는다.
예외는 경계(시스템 입력, 외부 API 호출)에서 미리 처리한다.

```
// 올바른 예 — 경계에서 처리
class UserRepository:
    function fetchUser(id) -> Result:
        try:
            return Success(api.getUser(id))
        catch error:
            log.error("Failed to fetch user {id}", error)
            return Failure(error)

// 잘못된 예 — 내부 로직에서 예외 전파
class OrderService:
    function processNext():
        next = queue.next()
        if next == null:
            throw Error("Queue is empty")  // 호출자가 예외를 잡아야 함 — 계약이 불명확
```

**리뷰 체크포인트**
- 내부 비즈니스 로직에서 예외를 던지는가? (경계가 아닌 곳)
- 외부 API 호출이 try-catch 또는 동등한 메커니즘으로 감싸여 있는가?
- 예외가 상위로 전파될 때 그 이유가 명확한가?

---

## 5. 에러 표현 (Error Representation)

에러를 타입으로 명확히 표현한다. **null은 "없음"의 이유를 말해주지 않는다** — 상태가 여러 가지일 수 있다면 반드시 타입으로 구분한다.

선호 순서:

1. **구분된 에러 타입 (Result/Either/sealed class 등)** — 이상적, 성공/실패가 타입으로 구분됨
2. **단순 Result 래퍼** — 성공/실패만 구분하면 되는 경우
3. **nullable/optional** — "없음"이 유일한 실패 상태이고, 그것이 정상일 때만 사용
4. **예외** — 프로그래밍 오류(계약 위반)에만 사용

**nullable 허용 기준**: "이 null이 왜 null인지 호출자가 알 필요가 없는가?" — Yes면 nullable 허용, No면 타입으로 구분.

```
// 이상적 — 실패 원인이 타입으로 구분됨
type FetchResult = Success(data) | NotFound(id) | NetworkError(cause)

// 허용 — 단순 성공/실패
function loadConfig() -> Result:
    try: return Success(parseConfig())
    catch: return Failure()

// OK — "없음"이 유일한 상태이고 정상
function findById(id) -> Item?       // 검색 결과가 없을 수 있음

// 잘못된 예 — null이 여러 상태를 숨김
function getCurrent() -> Item?       // null이 "로딩 중"인지 "에러"인지 "없음"인지 알 수 없음
```

**리뷰 체크포인트**
- null/None이 여러 실패 상태를 숨기고 있는가? (타입으로 구분해야 함)
- 성공과 실패 경로가 타입으로 구분되어 있는가?
- "이 null이 왜 null인지" 호출자가 구분해야 하는 상황인가?

---

## 6. 테스트 철학 (Test Philosophy)

핵심 기능을 자동화 테스트로 검증한다. 커버리지 100%는 목표가 아니다.

단위/통합/E2E 같은 레벨이 아니라, **"이 테스트가 무엇을 증명하는가"**가 기준이다.

**목적 기반 테스트**

| 목적 | 방법 |
|------|------|
| 상태 전환이 올바른가 | 상태 관리 테스트 |
| 화면 흐름이 정상인가 | UI 테스트 |
| 슬라이스 간 연동이 되는가 | 통합 테스트 |
| 잘못된 입력에도 안전한가 | 경계값/에러 케이스 테스트 |

각 테스트가 증명하는 것이 다르므로 모두 필요하다. "이게 깨지면 앱이 성립하지 않는가?" 순서로 우선순위를 정한다.

**테스트하지 않는 것**
- 내부 구현 세부사항 (private 필드, 메서드 호출 순서)
- 단순 getter/setter
- 라이브러리 코드 동작

```
// 올바른 예 — 행동을 검증
test "셔플 모드에서 다음 곡은 무작위 순서를 따른다":
    player.setShuffle(true)
    player.next()
    assert player.currentTrack != previousTrack

// 올바른 예 — 경계 조건 검증
test "쿠폰 만료 시각이 정확히 현재 시각과 같으면 만료로 처리된다":
    coupon = Coupon(expiredAt = now)
    assert coupon.isExpired() == true

// 잘못된 예 — 구현 세부사항을 테스트
test "_isExpired가 true로 설정된다":
    ...
```

**리뷰 체크포인트**
- 테스트가 "무엇을 증명하는가"가 명확한가?
- 테스트가 행동(behavior)을 검증하는가, 구현 세부사항(implementation detail)을 검증하는가?
- 테스트 이름이 상황과 기대 결과를 한글로 서술되어 있는가?
- 핵심 기능("이게 깨지면 앱이 성립하지 않는가")의 테스트가 있는가?

---

## 7. 주석 (Comments)

주석은 최소화한다. 필요한 경우는 두 가지뿐이다.

1. **공개 API** — 파라미터·반환값·예외를 문서화
2. **코드로 설명 불가한 이유** — "왜(why)"를 설명, "무엇(what)"은 코드가 설명

"코드로 설명 불가한 이유"의 대표적인 경우:
- 성능 최적화로 가독성이 희생된 경우
- 외부 API의 알려진 버그를 우회하는 경우
- 보안 제약으로 인한 비직관적 구현

```
// 올바른 예 — 이유를 설명
// OAuth 토큰은 만료 10분 전에 갱신해야 race condition을 방지할 수 있다
refreshToken(expiresAt - 10.minutes)

// 성능 최적화 — bitmap pooling으로 GC 압박을 줄임
val bitmap = bitmapPool.get(width, height)

// 외부 API 버그 우회 — API v2.3에서 null이 "null" 문자열로 반환되는 이슈
if (response == "null") return null

// 잘못된 예 — 코드가 이미 말하고 있음
// 리스트를 정렬
list.sort()
```

**리뷰 체크포인트**
- 코드를 읽으면 이해되는데 주석이 달려 있는가? (제거 대상)
- 공개 API에 문서 주석이 있는가?
- `TODO`, `FIXME` 주석이 방치되어 있는가?
