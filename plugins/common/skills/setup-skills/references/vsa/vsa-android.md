# VSA Android 아키텍처

> Android(Kotlin) 프로젝트에 적용되는 VSA 규칙.
> 공통 원칙은 `vsa-common-architecture.md` 참조.

---

## 폴더 구조

```
com.example.app/
├── app/
│   ├── home/
│   │   ├── HomeActivity.kt
│   │   └── HomeViewModel.kt
│   ├── navigation/
│   │   └── nav_graph.xml
│   └── di/
│       └── AppModule.kt
│
├── features/
│   ├── auth/
│   │   ├── login/
│   │   │   ├── LoginFragment.kt
│   │   │   ├── LoginViewModel.kt
│   │   │   └── LoginUiState.kt
│   │   ├── register/
│   │   │   ├── RegisterFragment.kt
│   │   │   └── RegisterViewModel.kt
│   │   └── shared/           ← register 생기면 생성
│   │       ├── AuthRepository.kt       (interface)
│   │       ├── AuthRepositoryImpl.kt
│   │       └── UserModel.kt
│   └── product/
│       ├── list/
│       └── shared/
│
└── shared/
    ├── contracts/
    │   └── IUserProvider.kt
    ├── models/
    │   └── UserSummary.kt
    ├── network/
    │   └── ApiClient.kt
    ├── events/
    │   ├── AppEvent.kt
    │   └── EventBus.kt
    └── di/
        └── NetworkModule.kt
```

---

## 슬라이스 단위

**Fragment(또는 Activity) + ViewModel + UiState** 묶음

```kotlin
features/auth/login/
  LoginFragment.kt    ← UI
  LoginViewModel.kt   ← 상태 + 로직
  LoginUiState.kt     ← 상태 정의
  LoginUseCase.kt     ← 복잡할 때만
```

---

## Repository 패턴

```kotlin
// interface — 계약
interface AuthRepository {
    suspend fun login(email: String, pw: String): Result<User>
    suspend fun getCurrentUser(): Result<User>
}

// 구현체 — 피처군 shared 소유
class AuthRepositoryImpl @Inject constructor(
    private val api: AuthApi
) : AuthRepository {
    override suspend fun login(...): Result<User> {
        return try {
            val user = api.login(...)
            Result.Success(user)
        } catch (e: Exception) {
            Result.Error(e)
        }
    }
}

// Hilt 연결 — app/di/ 소유
@Module @InstallIn(SingletonComponent::class)
abstract class AuthModule {
    @Binds
    abstract fun bindAuthRepository(
        impl: AuthRepositoryImpl
    ): AuthRepository
}
```

### Manager 패턴 (복잡한 도메인 로직)

```kotlin
interface SessionManager {
    fun getToken(): String?
    fun saveToken(token: String)
    fun clearSession()
}

class SessionManagerImpl @Inject constructor(
    private val storage: LocalStorage
) : SessionManager { ... }
```

---

## 상태 관리

```kotlin
// UiState — sealed class
sealed class LoginUiState {
    object Idle : LoginUiState()
    object Loading : LoginUiState()
    data class Success(val user: User) : LoginUiState()
    data class Error(val message: String) : LoginUiState()
}

// ViewModel
@HiltViewModel
class LoginViewModel @Inject constructor(
    private val authRepo: AuthRepository  // 인터페이스만 앎
) : ViewModel() {

    private val _uiState = MutableStateFlow<LoginUiState>(LoginUiState.Idle)
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    fun login(email: String, pw: String) = viewModelScope.launch {
        _uiState.value = LoginUiState.Loading
        when (val result = authRepo.login(email, pw)) {
            is Result.Success -> _uiState.value = LoginUiState.Success(result.data)
            is Result.Error -> _uiState.value = LoginUiState.Error(result.exception.message ?: "")
        }
    }
}
```

---

## 슬라이스 간 통신

### 데이터 요청 — Interface + Hilt

```kotlin
// shared/contracts/IUserProvider.kt
interface IUserProvider {
    suspend fun getCurrentUser(): UserSummary
}

// features/auth/shared/AuthUserProvider.kt
class AuthUserProvider @Inject constructor(
    private val repo: AuthRepository
) : IUserProvider {
    override suspend fun getCurrentUser(): UserSummary {
        val user = repo.getCurrentUser().getOrThrow()
        return UserSummary(id = user.id, name = user.name)
    }
}
```

### 이벤트 전파 — SharedFlow EventBus

```kotlin
// shared/events/AppEvent.kt
sealed class AppEvent {
    data class UserLoggedIn(val userId: String) : AppEvent()
    data class OrderCompleted(val orderId: String) : AppEvent()
}

// shared/events/EventBus.kt
@Singleton
class EventBus @Inject constructor() {
    private val _events = MutableSharedFlow<AppEvent>(extraBufferCapacity = 64)
    val events = _events.asSharedFlow()

    fun emit(event: AppEvent) { _events.tryEmit(event) }
}
```

> **슬라이스 내부 1회성 이벤트** (화면 전환, 스낵바): `Channel` 사용
> **슬라이스 간 전역 이벤트** (로그인, 구매 완료): `SharedFlow EventBus` 사용

### 화면 이동 — NavGraph action ID

```kotlin
// action ID만 앎 — LoginFragment 직접 참조 없음
findNavController().navigate(R.id.to_home)
```

---

## Cross-cutting Concerns

```kotlin
// 네트워크 로깅 + 인증 — OkHttp Interceptor
OkHttpClient.Builder()
    .addInterceptor(HttpLoggingInterceptor())
    .addInterceptor(AuthInterceptor())
    .addInterceptor(ErrorInterceptor())
    .build()

// 에러 상태 — sealed Result
sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val exception: Exception) : Result<Nothing>()
}
```

---

## 테스트

```
단위 테스트: JUnit + MockK → Fake 사용
E2E:         Espresso

test/
  fakes/
    FakeAuthRepository.kt
  features/auth/login/
    LoginViewModelTest.kt
androidTest/
  AuthFlowTest.kt       ← Espresso E2E
```

```kotlin
// Fake — Mock 대신
class FakeAuthRepository : AuthRepository {
    private val users = mutableMapOf<String, User>()

    override suspend fun login(email: String, pw: String): Result<User> {
        val user = users[email] ?: return Result.Error(Exception("Not found"))
        return Result.Success(user)
    }

    fun addUser(email: String, user: User) { users[email] = user }
}
```

---

## 네이밍 컨벤션

| 항목 | 규칙 | 예시 |
| --- | --- | --- |
| 파일명 | PascalCase | `LoginFragment.kt` |
| 패키지 | lowercase | `features.auth.login` |
| 클래스 | PascalCase | `class LoginViewModel` |
| 구현체 | Impl 접미사 | `AuthRepositoryImpl` |
| 인터페이스 | 선택적 I 접두사 | `AuthRepository` or `IUserProvider` |
| 변수/함수 | camelCase | `fun loadProducts()` |
| 상수 | SCREAMING_SNAKE_CASE | `const val MAX_RETRY = 3` |
| UiState | 슬라이스명 + UiState | `sealed class LoginUiState` |
| AppEvent | 도메인 + 과거형 | `data class UserLoggedIn(...)` |
