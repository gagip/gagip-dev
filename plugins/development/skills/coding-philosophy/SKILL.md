---
name: coding-philosophy
description: >
  코드 품질 판정의 공통 기준이 되는 개인 코딩 철학. "코딩 철학", "리뷰 기준", "품질 기준"을
  묻거나, 코드 리뷰·설계 검토·인터페이스 점검에서 무엇을 결함으로 볼지 판단해야 할 때 사용한다.
  다른 스킬(`development:module-review` 등)이 판정 기준으로 이 스킬을 로드한다.
allowed-tools: Read
---

# 코딩 철학 가이드라인

개인 코딩 철학. 코드 리뷰·설계 검토 시 이 기준으로 가독성·정확성·구조를 평가한다.

**언어와 프레임워크에 무관하게 적용되는 원칙**이며, 코드 예시는 의사코드(pseudocode)로 표기한다.
특정 언어의 문법을 강요하지 않는다 — 대상 레포에 이미 관례가 있으면 그 관례로 이 원칙을 구현한다.

의사코드의 `assert`는 **릴리즈에서도 항상 활성화된 검증 수단**을 의미한다. 언어마다 대응 수단이
다르다(인자 검사·상태 검사 내장 함수, 프로젝트 전용 검증 유틸 등). 디버그 전용으로 비활성화되는
수단은 원칙적으로 쓰지 않는다.

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

**검증 수단은 대상 레포의 관례를 따른다.** 프로젝트가 전용 검증 유틸을 정해뒀다면 그것을 쓰고,
언어 내장 수단을 쓰기로 했다면 그것을 쓴다. 한 레포 안에서 수단이 섞이는 것 자체가 결함이다.

**비대칭이 곧 결함이다.** 같은 인터페이스의 구현체들, 같은 모듈의 동급 함수들 중 **하나만**
검증이 빠져 있다면 그것은 취향 차이가 아니라 결함이다. 나머지가 검증한다는 사실이 그 검증이
필요하다는 증거다.

**리뷰 체크포인트**
- 공개 함수 인자에 사전조건 검사가 있는가?
- 상태 의존적 메서드에 불변식 검사가 있는가?
- 반환값이 항상 유효한 범위임을 사후조건으로 보장하는가?
- 에러 메시지에 실제 값이 포함되어 있는가?
- 형제 요소들 사이에 검증 유무가 갈리는가?

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
- 검증이 없어 실패가 **지연 노출**되지 않는가? (잘못된 값이 통과해 한참 뒤 외부 시스템에서 거부됨)

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

**한 모듈 안에서 실패 표현 방식이 섞이면 안 된다.** 같은 성격의 실패를 어떤 함수는 예외로,
어떤 함수는 빈 값 반환으로 알리면 호출자가 매번 다르게 대응해야 한다. 새 방식을 도입하기보다
**그 레포가 이미 쓰는 방식으로 통일**하는 쪽을 우선한다.

**리뷰 체크포인트**
- null/None이 여러 실패 상태를 숨기고 있는가? (타입으로 구분해야 함)
- 성공과 실패 경로가 타입으로 구분되어 있는가?
- "이 null이 왜 null인지" 호출자가 구분해야 하는 상황인가?
- 같은 모듈 안에서 예외 반환과 빈 값 반환이 섞여 있는가?

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

각 테스트가 증명하는 것이 다르므로 모두 필요하다. "이게 깨지면 제품이 성립하지 않는가?" 순서로 우선순위를 정한다.

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
- 핵심 기능("이게 깨지면 제품이 성립하지 않는가")의 테스트가 있는가?

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

---

## 8. 공개 인터페이스 최소화 (Minimal Public Surface)

모듈이 밖으로 내보내는 것은 **단순 · 최소 · 명확**해야 한다. 공개된 것은 계약이 되고,
계약은 한번 생기면 되돌리기 어렵다.

**판정 기준은 "운영 코드가 실제로 호출하는가"** 하나뿐이다. 각 공개 심볼을 검색해
호출처를 센다. 0건이면 비공개 전환 또는 제거 후보다.

**테스트에서만 쓰인다는 것은 공개 유지의 근거가 아니다.** 테스트는 하위 모듈에서 직접
import하면 된다. 테스트 편의를 위해 공개 표면을 넓히는 것은 원칙 10을 오해한 결과다.

예외는 **출력 계약의 일부**인 것뿐이다 — 이름으로 import되지 않더라도 공개 함수의
반환 타입이라면 이미 계약에 포함돼 있다.

```
// 제거 후보 — 운영 코드 호출처 0건, 내부에서만 쓰임
export function collect(...)      // 같은 모듈의 download()가 부르는 게 전부
export const FEE_RATE             // 테스트만 참조

// 유지 — 반환 타입이라 이미 계약의 일부
export type BacktestResult        // run()의 반환 타입
```

**리뷰 체크포인트**
- 각 공개 심볼의 운영 코드 호출처가 존재하는가?
- 공개해둔 이유가 "테스트가 쓰니까"인가?
- 패키지 루트에서 재노출한 것 중 실제로 그 경로로 쓰이는 것이 있는가?
- 최상위/루트 패키지의 재노출도 점검했는가? (하위 모듈만 보다 놓치기 쉽다)

---

## 9. 시그니처 자기설명 (Self-Describing Signatures)

**이름과 타입만 보고 무엇을 하는지 유추할 수 있어야 한다.** 문서를 읽어야 알 수 있다면
시그니처가 제 일을 못 하고 있는 것이다. 5장(에러 표현)과 같은 결 — **타입이 말하게 한다.**

**안티패턴 1 — 방향·단위가 없는 이름**

```
// 나쁨 — 과거인지 미래인지, 기간인지 시점인지 알 수 없음
function download(code, years = 3)

// 좋음 — 방향이 이름에 있음
function download(code, lookbackYears = 3)

// 나쁨 — 단가인가 총액인가?
type Position = { purchasePrice, currentPrice }

// 좋음 — 이름이 실제 값과 일치
type Position = { purchaseAmount, currentValue }
```

이름이 실제 값과 다르면 단순한 가독성 문제가 아니라 **버그의 원인**이 된다.
총액인 필드를 단가로 착각해 수량을 한 번 더 곱하는 식의 실수가 리뷰를 통과한다.

**안티패턴 2 — 모호한 컨테이너**

호출자마다 기대하는 키가 다른 raw `dict`/`map`, 의미가 위치로만 구분되는 tuple은
타입이 아니라 타입의 부재다. 무엇을 넣어야 하는지 시그니처가 답하지 못한다.

```
// 나쁨 — 구현체마다 기대 키가 다름. 호출부가 구현체를 알아야 함
function evaluate(price, extra: Map<String, Any>)

// 좋음 — 필요한 데이터를 명시적 타입으로
function evaluate(price, history: PriceHistory)

// 나쁨 — 두 번째 원소가 왜 없을 수 있는지 타입이 말하지 않음
function downloadAll(codes) -> List<(String, Path?)>

// 좋음 — 항목별 성공/실패를 타입으로
function downloadAll(codes) -> List<DownloadResult>
```

**리뷰 체크포인트**
- 파라미터 이름만 보고 방향·단위·의미를 알 수 있는가?
- 필드 이름이 실제로 담긴 값과 일치하는가? (가격 vs 금액, 개수 vs 인덱스)
- raw map/dict/tuple로 뭉뚱그린 인자·반환값이 있는가?
- 범용 인터페이스인데 호출부가 특정 구현체의 기대 키를 알아야 하는가?

---

## 10. 테스트 가능성은 설계에서 나온다 (Testability by Design)

테스트 가능성은 **가시성(public/private) 문제가 아니다.** 무언가를 공개했다고 테스트가
쉬워지지 않고, 비공개라고 테스트가 불가능해지지도 않는다.

테스트 가능성을 만드는 것은 설계다:
- **의존성 주입** — 외부 세계(네트워크·DB·시계)를 생성자나 인자로 받는다
- **순수 함수** — 같은 입력에 같은 출력, 부수효과 없음
- **부수효과 격리** — I/O를 얇은 층으로 밀어내고 판단 로직과 섞지 않는다
- **작은 단위의 컴포지션** — 한 함수가 하나만 한다

언어가 접근제어를 강제하든 안 하든 동일하게 적용되는 보편 원칙이다.

```
// 나쁨 — 생성자 안에서 외부 의존성을 직접 생성. 대체할 방법이 없다
class Broker:
    function init(apiKey, apiSecret):
        this.client = HttpClient(apiKey, apiSecret)   // 테스트에서 가로챌 수 없음

// 좋음 — 주입받으므로 목(mock)으로 대체 가능
class Broker:
    function init(client: HttpClient):
        this.client = client

    static function fromCredentials(apiKey, apiSecret) -> Broker:
        return Broker(HttpClient(apiKey, apiSecret))   // 편의 생성은 별도 경로로
```

**테스트가 0개인 모듈을 만나면 "테스트를 추가하라"로 끝내지 않는다.** 왜 아무도 쓰지
않았는지 구조적 원인을 먼저 찾는다 — 생성자 내부 의존성 생성, 전역 상태 접근,
네트워크·시간·랜덤의 하드코딩. 원인을 두고 테스트만 얹으면 테스트도 같이 망가진다.

**"통합 테스트가 있다"는 안심의 근거가 아니다.** 자격증명이나 외부 환경이 없으면 자동
skip되는 테스트는 평소 개발 흐름에서 한 줄도 실행되지 않는다.

**리뷰 체크포인트**
- 외부 의존성을 주입받는가, 내부에서 생성하는가?
- 판단 로직과 I/O가 같은 함수 안에 섞여 있는가?
- 테스트가 0개인 모듈이 있는가? 그 구조적 원인은 무엇인가?
- 그 모듈의 테스트가 조건부로 skip되고 있지는 않은가?

---

## 11. 가짜 테스트 금지 (No Self-Proving Tests)

**프로덕션 코드를 호출하지 않는 테스트는 아무것도 증명하지 못한다.**
공식이나 로직을 테스트 안에 복붙해 자기 자신과 비교하는 테스트가 대표적이다.
프로덕션에 버그가 생겨도 영원히 통과하므로, 없는 것보다 나쁘다 — **잘못된 안심**을 준다.

```
// 잘못된 예 — 프로덕션을 부르지 않고 같은 공식을 다시 계산
test "최대 낙폭이 올바르게 계산된다":
    peak = max(values)
    expected = (peak - min(values)) / peak      // 프로덕션 공식을 복붙
    assert expected == (peak - min(values)) / peak   // 자기 자신과 비교

// 올바른 예 — 실제 반환값을 검증
test "최대 낙폭이 올바르게 계산된다":
    result = backtester.run(priceData)
    assert result.maxDrawdown == 0.25           // 손으로 계산한 기대값
```

기대값은 **프로덕션 로직이 아니라 명세에서** 나와야 한다. 손으로 계산하거나, 알려진
입력-출력 쌍을 쓰거나, 경계 조건의 정의로부터 유도한다.

**리뷰 체크포인트**
- 이 테스트가 프로덕션 함수를 실제로 호출하는가?
- 기대값이 프로덕션과 같은 공식으로 계산되고 있지는 않은가?
- 프로덕션 코드에 일부러 버그를 넣으면 이 테스트가 실패하는가?
