# 테스트 가이드

## 테스트 기준점

### 테스트해야 하는 것

- 상태 전환 로직 (예: IDLE → RUNNING → PAUSED)
- 비즈니스 규칙
- 경계 조건 (0, 최솟값, 최댓값, 빈 컬렉션)
- 에러 경로 (예외 발생, 실패 상태 처리)

### 테스트하지 않는 것

- `core/` 인프라 코드 (DI 설정, DB 설정)
- Compose UI 렌더링 세부사항
- 단순 getter/setter
- 라이브러리 코드 동작

---

## 테스트 파일 위치

```
app/src/
├── test/java/com/{package}/          ← JVM 테스트 (도메인, ViewModel)
│   └── features/{feature}/
│       ├── domain/     ← 도메인 로직 테스트
│       ├── data/       ← FakeRepository 위치
│       └── ui/         ← ViewModel 테스트
└── androidTest/java/com/{package}/   ← Compose UI, E2E
    └── features/{feature}/
```

### 배치 기준

- **`test/`**: 순수 Kotlin 로직, ViewModel, Fake 기반 테스트
- **`androidTest/`**: Compose UI 렌더링, 실제 DB 접근, E2E 흐름

### 파일 명명

대상 클래스명 + `Test` 접미사. 슬라이스 통합 테스트는 `SliceTest` 접미사.

```
SomeManagerTest.kt
SomeViewModelTest.kt
SomeFeatureSliceTest.kt
```

---

## 테스트 작성 규칙

### 테스트 스타일

Kotest **BehaviorSpec**을 사용한다. `Given` / `When` / `Then` 은 **대문자**로 시작한다.

```kotlin
class SomeManagerTest : BehaviorSpec({

    Given("RUNNING 상태일 때") {
        When("pause를 호출하면") {
            Then("PAUSED 상태로 전환된다") {
                runTest {
                    // ...
                }
            }
        }
    }
})
```

비활성화가 필요한 테스트는 `xGiven`을 사용한다.

```kotlin
xGiven("...") { ... }
```

### 테스트 이름

- `Given`: 사전 조건(상태)을 서술한다.
- `When`: 실행하는 동작을 서술한다.
- `Then`: 기대 결과를 서술한다.

### 검증 대상

행동(behavior)을 검증한다. 내부 구현 세부사항(private 필드, 메서드 호출 순서)은 검증하지 않는다.

```kotlin
// 올바른 예 — 동작을 검증
@Test
fun `FOCUS 세션 skip 시 BREAK로 전환된다`() {
    manager.skip()
    manager.state.value.session shouldBe Session.BREAK
}

// 잘못된 예 — 내부 필드를 직접 검증
@Test
fun `_internalCount가 1이 된다`() {
    manager.skip()
    manager.state.value.internalCount shouldBe 1
}
```

### 커버리지 기준

모든 코드를 커버하는 것이 목표가 아니다. **핵심 흐름과 경계 조건**이 커버되는지를 기준으로 판단한다.

---

## Fake vs Mock 전략

Repository는 인터페이스로 정의되므로 **Fake 구현을 우선**한다.

### Fake 구현 예시

```kotlin
// test/.../features/{feature}/data/FakeSomeRepository.kt
class FakeSomeRepository : SomeRepository {
    private val items = mutableListOf<Item>()

    override suspend fun getAll(): List<Item> = items.toList()
    override suspend fun save(item: Item) { items.add(item) }
    override suspend fun delete(id: Long) { items.removeAll { it.id == id } }
}
```

### Mockk 사용 기준

다음 경우에만 선택적으로 사용한다:

- Android 시스템 클래스 (`Context`, `ContentResolver`)
- 외부 라이브러리 구체 클래스

```kotlin
val mockContext = mockk<Context>()
every { mockContext.getSystemService(AudioManager::class.java) } returns mockAudioManager
```

### StateFlow 테스트

#### `SharingStarted.Eagerly` — `.value` 직접 읽기

구독자 없이도 항상 최신값을 유지하므로 `.value`로 즉시 읽는다.

```kotlin
// 도메인/Manager 계층 — Eagerly StateFlow
manager.start()
advanceUntilIdle()

manager.state.value.timerState shouldBe TimerState.RUNNING
```

#### `SharingStarted.WhileSubscribed` — Turbine 사용

구독자가 없으면 업스트림이 멈추므로 `.value`로는 갱신된 값을 읽을 수 없다.
**Turbine**의 `test { }` 블록을 사용한다. 블록 진입 시 자동으로 구독이 활성화된다.

```kotlin
// ViewModel 계층 — WhileSubscribed StateFlow
viewModel.uiState.test {
    awaitItem() // 초기값 소비
    viewModel.start()
    awaitItem().timerState shouldBe TimerState.RUNNING
    cancelAndIgnoreRemainingEvents()
}
```

`cancelAndIgnoreRemainingEvents()`는 검증 후 남은 이벤트를 무시하고 구독을 종료한다.
여러 필드를 함께 검증할 때는 `awaitItem().also { }` 를 사용한다.

```kotlin
viewModel.uiState.test {
    awaitItem() // IDLE
    viewModel.start()
    awaitItem() // RUNNING
    viewModel.reset()
    awaitItem().also {
        it.timerState shouldBe TimerState.IDLE
        it.count shouldBe 0
    }
    cancelAndIgnoreRemainingEvents()
}
```

#### 판단 기준

| `SharingStarted` | 검증 방식 |
|------------------|----------|
| `Eagerly` | `.value` 직접 읽기 |
| `WhileSubscribed` | Turbine `test { awaitItem() }` |

---

## 계층별 예시

### 도메인 로직 테스트

```kotlin
// test/.../features/{feature}/domain/SomeManagerTest.kt
class SomeManagerTest {

    private lateinit var manager: SomeManager

    @Before
    fun setUp() {
        manager = SomeManager()
    }

    @Test
    fun `특정 동작 수행 시 상태가 변경된다`() = runTest {
        manager.doSomething()
        manager.state.value.phase shouldBe Phase.NEXT
    }
}
```

### ViewModel 테스트 (FakeRepository + Turbine 사용)

`viewModelScope`는 `Dispatchers.Main`을 사용하므로 `beforeSpec`에서 `setMain`이 필요하다.
`uiState`는 `WhileSubscribed`이므로 Turbine으로 검증한다.

```kotlin
// test/.../features/{feature}/ui/SomeViewModelTest.kt
@OptIn(ExperimentalCoroutinesApi::class)
class SomeViewModelTest : BehaviorSpec({

    val testDispatcher = UnconfinedTestDispatcher()

    beforeSpec { Dispatchers.setMain(testDispatcher) }
    afterSpec { Dispatchers.resetMain() }

    Given("아이템이 없을 때") {
        When("saveItem()를 호출하면") {
            Then("목록에 추가된다") {
                runTest(testDispatcher) {
                    val viewModel = SomeViewModel(FakeSomeRepository())

                    viewModel.uiState.test {
                        awaitItem() // 초기값
                        viewModel.saveItem("새 아이템")
                        awaitItem().items.first().name shouldBe "새 아이템"
                        cancelAndIgnoreRemainingEvents()
                    }
                }
            }
        }
    }
})
```

### E2E 테스트 — 주요 사용자 흐름만 (androidTest)

```kotlin
// androidTest/.../SomeFeatureE2ETest.kt
@HiltAndroidTest
class SomeFeatureE2ETest {

    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun `아이템 생성 후 목록 화면에 표시된다`() {
        composeRule.onNodeWithText("새 아이템").performClick()
        composeRule.onNodeWithTag("item_name_input").performTextInput("테스트")
        composeRule.onNodeWithText("저장").performClick()

        composeRule.onNodeWithText("테스트").assertIsDisplayed()
    }
}
```
