# Android / Compose 패턴

ZenPlayer 프로젝트에서 실제로 사용되는 Android/Compose 설계 패턴.

---

## ViewModel

### 기본 구조

```kotlin
@HiltViewModel
class PomodoroViewModel @Inject constructor(
    private val pomodoroManager: PomodoroManager
) : ViewModel() {

    val uiState = pomodoroManager.pomodoroState
        .map { state -> PomodoroUiState(...) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed5s, PomodoroUiState())

    init {
        viewModelScope.launch { pomodoroManager.restore() }
    }

    fun start() = viewModelScope.launch { pomodoroManager.start() }
    fun pause() = viewModelScope.launch { pomodoroManager.pause() }
}
```

### UseCase 도입 기준

의존성 흐름: `ViewModel → UseCase → Repository (interface)`

**도입하는 경우**
- ViewModel이 여러 Repository나 인프라 의존성(Context 등)을 직접 참조할 때
- 동일한 비즈니스 로직을 여러 ViewModel이 재사용해야 할 때

**도입하지 않는 경우**
- Repository 하나만 단순하게 호출하는 화면 (UseCase가 boilerplate만 늘림)

```kotlin
// ViewModel은 UseCase만 의존
class MusicListViewModel @Inject constructor(
    private val loadTracksUseCase: LoadTracksUseCase,
)

// UseCase는 Repository 인터페이스만 의존
class LoadTracksUseCase @Inject constructor(
    private val musicRepository: MusicRepository,
)
```

### 규칙

- `@HiltViewModel` + `@Inject constructor` 필수
- suspend 함수는 반드시 `viewModelScope.launch { }` 안에서 호출
- `stateIn` 표준: `SharingStarted.WhileSubscribed5s`, `initialValue` 항상 제공
- 이벤트(일회성 메시지)는 `MutableSharedFlow<T>` + `SharedFlow`로 노출

```kotlin
private val _events = MutableSharedFlow<String>()
val events: SharedFlow<String> = _events.asSharedFlow()
```

---

## Composable 함수

### Stateless Composable (기본)

- 상태는 파라미터로 받고, 이벤트는 람다로 받음
- `modifier: Modifier = Modifier`는 항상 마지막 파라미터

```kotlin
@Composable
fun PomodoroTimer(
    uiState: PomodoroUiState,
    onPlayPause: () -> Unit,
    onSkip: () -> Unit,
    onReset: () -> Unit,
    modifier: Modifier = Modifier
) { ... }
```

### Stateful Screen Composable

- ViewModel에서 state 수집: `collectAsStateWithLifecycle()` 사용
- 부수효과: `LaunchedEffect`
- 로컬 상태: `remember { }`

```kotlin
@Composable
fun PlayerScreen(
    viewModel: PlayerViewModel,
    onNavigateBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(Unit) {
        viewModel.events.collect { message ->
            snackbarHostState.showSnackbar(message)
        }
    }

    Scaffold(...) { ... }
}
```

### Private Helper Composable

- 파일 내부에서만 쓰이는 Composable은 `private` 선언

```kotlin
@Composable
private fun CircularProgressArc(
    progress: Float,
    color: Color,
    modifier: Modifier = Modifier
) { ... }
```

### 규칙

| 항목 | 규칙 |
|------|------|
| 파라미터 수 | 최대 5~7개 권장 |
| modifier | 항상 마지막 파라미터, 기본값 `Modifier` |
| 상태 수집 | `collectAsStateWithLifecycle()` |
| 부수효과 | `LaunchedEffect` |
| 로컬 상태 | `remember { }` |
| 내부 helper | `@Composable private fun` |

---

## Hilt DI

### Module 정의

```kotlin
@Module
@InstallIn(SingletonComponent::class)
object TimerModule {

    // 도메인 클래스에 주입할 Application 수명 scope
    // 도메인 클래스는 CoroutineScope를 직접 생성하지 않고 주입받는다 (테스트 가능성 확보)
    @Provides @Singleton @ApplicationScope
    fun provideApplicationScope(): CoroutineScope =
        CoroutineScope(SupervisorJob() + Dispatchers.Default)

    @Provides
    @Singleton
    fun provideTimerEngine(
        repository: TimerSnapshotRepository,
        @ApplicationScope scope: CoroutineScope,
    ): TimerEngine = TimerEngine(repository, scope = scope)

    @Provides
    @Singleton
    fun providePomodoroManager(
        timerEngine: TimerEngine,
        repository: PomodoroSnapshotRepository,
        @ApplicationScope scope: CoroutineScope,
    ): PomodoroManager = PomodoroManager(timerEngine, repository, scope)
}
```

### Activity / Service Injection

```kotlin
@AndroidEntryPoint
class ZenPlayerService : Service() {
    @Inject lateinit var timerEngine: TimerEngine
    @Inject lateinit var pomodoroManager: PomodoroManager
}
```

### 규칙

- Module은 `object` (class 아님)
- `@Singleton` — 앱 수명과 동일한 객체에 사용
- `@ApplicationContext` — Context 주입 시 사용
- Activity/Service는 `lateinit var`, ViewModel은 constructor injection

---

## 컬러 / 테마

### 전역 컬러 (`Color.kt`)

앱 전체에서 공유되는 팔레트는 `Color.kt`에 정의.

### Feature 로컬 컬러

특정 화면/컴포넌트에서만 쓰이는 컬러는 파일 상단에 `private val`로 정의.

```kotlin
private val FocusColor = Color(0xFFE53935)
private val ShortBreakColor = Color(0xFF43A047)
private val LongBreakColor = Color(0xFF1E88E5)
```

### MaterialTheme 활용

```kotlin
Text(
    style = MaterialTheme.typography.labelMedium,
    color = MaterialTheme.colorScheme.onTertiaryContainer,
)

val backgroundColor = if (isCurrentTrack)
    MaterialTheme.colorScheme.primaryContainer
else
    MaterialTheme.colorScheme.surface
```

---

## LazyColumn (리스트)

```kotlin
LazyColumn(modifier = Modifier.fillMaxSize()) {
    itemsIndexed(uiState.tracks) { index, track ->
        TrackItem(
            track = track,
            isCurrentTrack = track.id == uiState.currentTrack?.id,
            onClick = {
                viewModel.playTrack(startIndex = index)
                onNavigateToPlayer()
            }
        )
    }
}
```

---

## Navigation

- Screen은 sealed class로 route 관리
- ViewModel은 `hiltViewModel()`로 주입
- Screen 간 이동: `navController.navigate(route)`, 뒤로가기: `navController.popBackStack()`

```kotlin
sealed class Screen(val route: String) {
    data object Home : Screen("home")
    data object MusicList : Screen("musicList")
    data object Player : Screen("player")
}
```
