# Kotlin 코딩 컨벤션

ZenPlayer 프로젝트에서 실제로 사용되는 Kotlin 코딩 규칙.

---

## 네이밍

| 대상 | 규칙 | 예시 |
|------|------|------|
| 클래스/인터페이스 | PascalCase | `UserRepository`, `AudioPlayer` |
| 함수/변수 | camelCase | `fetchUser`, `itemCount` |
| Private 상태 | `_` 접두사 | `_uiState`, `_isLoading` |
| Public Flow | 접두사 없음 | `val uiState`, `val isLoading` |
| 상수 | UPPER_SNAKE_CASE in `companion object` | `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT` |
| 로그 태그 | `inline val Log*` | `inline val LogAuth get() = Timber.tag("Auth")` |

---

## Data Class

- 모든 파라미터에 기본값 제공
- 계산 속성은 `val` with getter로 포함 가능

```kotlin
data class UserUiState(
    val name: String = "",
    val email: String = "",
    val isLoading: Boolean = false,
) {
    val displayName: String
        get() = name.ifBlank { email }
}
```

---

## Sealed Class / Enum

**Enum** — 단순 상태 열거:
```kotlin
enum class LoadState { IDLE, LOADING, SUCCESS, ERROR }
```

**Enum with properties** — 값을 가진 상태:
```kotlin
enum class NetworkStatus(val label: String) {
    CONNECTED("연결됨"),
    DISCONNECTED("연결 끊김"),
    UNKNOWN("알 수 없음")
}
```

**Sealed Class** — 복합 상태 (데이터 포함):
```kotlin
sealed class Result<out T> {
    data object Loading : Result<Nothing>()
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val message: String) : Result<Nothing>()
}
```

---

## StateFlow / MutableStateFlow

- `MutableStateFlow`는 `private`, 외부에는 `asStateFlow()`로 노출

```kotlin
private val _uiState = MutableStateFlow(UiState())
val uiState: StateFlow<UiState> = _uiState.asStateFlow()
```

---

## Flow 조합

- `combine` + `stateIn` 조합이 표준

```kotlin
val screenState: StateFlow<ScreenState> = combine(
    repository.items,
    repository.selectedId,
) { items, selectedId ->
    ScreenState(items = items, selectedId = selectedId)
}.stateIn(scope, SharingStarted.Eagerly, ScreenState())
```

---

## CoroutineScope

- `SupervisorJob() + Dispatchers.*` 조합 사용
- Service: `Dispatchers.Main`, 도메인 로직: `Dispatchers.Default`
- **도메인 클래스는 CoroutineScope를 내부에서 직접 생성하지 않고 생성자로 주입받는다**
  - 이유: 테스트에서 `TestScope`를 주입해 가상 시간 제어 가능 (`Thread.sleep`, `waitUntil` 등의 불안정한 패턴 제거)
  - 프로덕션: DI에서 `@ApplicationScope` qualifier로 Application 수명 scope 주입
  - 테스트: `runTest { }` 블록의 `this`(TestScope) 주입

```kotlin
// 도메인 클래스 — CoroutineScope를 생성자로 주입
class DownloadManager(
    private val repository: DownloadRepository,
    private val scope: CoroutineScope,   // 외부 주입
)

// DI 모듈 — Application 수명 scope 제공
@Qualifier @Retention(RUNTIME) annotation class ApplicationScope

@Provides @Singleton @ApplicationScope
fun provideApplicationScope(): CoroutineScope =
    CoroutineScope(SupervisorJob() + Dispatchers.Default)

@Provides @Singleton
fun provideDownloadManager(
    repository: DownloadRepository,
    @ApplicationScope scope: CoroutineScope,
): DownloadManager = DownloadManager(repository, scope)

// 서비스 — 자체 scope는 직접 생성 (Service 수명과 일치)
private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
```

**dispose() 규칙**

- 도메인 클래스의 `dispose()`는 **scope.cancel()을 호출하지 않는다** — scope 수명은 주입한 쪽이 관리
- `dispose()`는 내부 Job만 취소

```kotlin
fun dispose() {
    activeJob?.cancel()
    activeJob = null
}
```

**테스트 패턴**

```kotlin
// TestScope를 주입 → runTest 가상 시간 제어 가능
@Test
fun `작업 완료 시 SUCCESS 상태가 된다`() = runTest {
    val manager = DownloadManager(fakeRepository, scope = this)
    manager.start()
    advanceUntilIdle()   // Thread.sleep / waitUntil 대체
    assertEquals(LoadState.SUCCESS, manager.state.value)
}
```

---

## 동시성 (Mutex)

- 상태 변경이 경합하는 suspend 함수는 `Mutex.withLock` 사용

```kotlin
private val mutex = Mutex()
private var isProcessing = false

private suspend fun processNext() {
    val item = mutex.withLock {
        if (isProcessing) return
        isProcessing = true
        queue.poll()
    }
    try {
        repository.process(item)
    } finally {
        mutex.withLock { isProcessing = false }
    }
}
```

---

## 에러 처리 (safeCatching)

`runCatching`은 `CancellationException`까지 잡아서 코루틴 취소가 깨진다. `safeCatching` 래퍼를 사용한다.

```kotlin
inline fun <T> safeCatching(block: () -> T): Result<T> =
    try {
        Result.success(block())
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        Result.failure(e)
    }
```

| 상황 | 선택 |
|------|------|
| suspend 함수에서 예외 처리 | `safeCatching` |
| 코루틴 아닌 코드에서 예외 처리 | `runCatching` 허용 |
| 복구 불가능한 예외 | 잡지 않고 전파 |

```kotlin
// 올바른 예
suspend fun fetchUser(id: String): Result<User> = safeCatching {
    api.getUser(id)
}

// 잘못된 예 — CancellationException이 잡힘
suspend fun fetchUser(id: String): Result<User> = runCatching {
    api.getUser(id)
}
```

---

## Null 처리

| 패턴 | 용도 |
|------|------|
| `?.` safe call | nullable 값 접근 |
| `?: "기본값"` elvis | null 대체값 |
| `?.let { }` | null 아닐 때 블록 실행 |
| `?: return` / `?: return@lambda` | early return |

```kotlin
// safe call
fun stopPlayback() = player?.stop()

// elvis
val label = error.message ?: "알 수 없는 오류"

// let
currentUser?.let { user ->
    ProfileContent(user = user)
} ?: EmptyState()
```

---

## 클래스 내 선언 순서

1. Public StateFlow / 상태 프로퍼티
2. Private 내부 상태
3. `init` 블록
4. Public suspend 함수
5. Public 일반 함수
6. Private 함수
7. `companion object`
