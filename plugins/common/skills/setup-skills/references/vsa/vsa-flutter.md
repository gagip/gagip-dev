# VSA Flutter 아키텍처

> Flutter(Dart + Riverpod) 프로젝트에 적용되는 VSA 규칙.
> 공통 원칙은 `vsa-common-architecture.md` 참조.

---

## 폴더 구조

```
lib/
├── app/
│   ├── router/
│   │   └── app_router.dart
│   └── di/
│       └── app_module.dart
│
├── features/
│   ├── auth/
│   │   ├── data/
│   │   │   ├── auth_repository.dart
│   │   │   └── auth_mapper.dart
│   │   ├── domain/
│   │   │   ├── user.dart
│   │   │   └── auth_exception.dart
│   │   └── presentation/
│   │       ├── screens/
│   │       │   ├── login_screen.dart
│   │       │   └── register_screen.dart
│   │       └── providers/
│   │           ├── auth_provider.dart
│   │           └── login_form_provider.dart
│   └── product/
│       ├── data/
│       │   └── product_repository.dart
│       ├── domain/
│       │   └── product.dart
│       └── presentation/
│           ├── screens/
│           │   ├── product_list_screen.dart
│           │   └── product_detail_screen.dart
│           └── providers/
│               └── product_list_provider.dart
│
├── shared/
│   ├── database/          ← DB 스키마 및 연결 (여러 feature 공유)
│   ├── providers/         ← 전역 공유 Provider (Repository 등)
│   ├── models/            ← 최소 공유 모델 (*_summary, *_info)
│   ├── network/
│   │   └── api_client.dart
│   └── utils/
│       └── validators.dart
│
└── main.dart
```

---

## 슬라이스 단위

**도메인 기준**으로 슬라이스를 나누고, 각 슬라이스 내부에 `data/domain/presentation` 레이어를 둔다.

```
features/auth/
  data/
    auth_repository.dart   ← DB/API 접근, 도메인 에러로 변환
    auth_mapper.dart       ← DB 모델 ↔ 도메인 모델 변환
  domain/
    user.dart              ← 도메인 모델 (Freezed)
    auth_exception.dart    ← 도메인 에러
  presentation/
    screens/
      login_screen.dart    ← UI (ConsumerWidget)
    providers/
      auth_provider.dart   ← Riverpod Provider + 상태 + 로직
```

슬라이스 분리 트리거 (vsa-common.md 참조):
- 단일 파일 ~500줄 초과
- 두 기능이 서로 다른 이유로 변경될 때
- 같은 로직을 다른 슬라이스에서 복붙할 때 (두 번째 발생 시)

---

## Repository 패턴

구현체가 하나인 경우(로컬 DB 등) — 구현체만 사용한다. 테스트는 Riverpod `overrideWithValue`로 Fake를 주입한다.

```dart
// features/auth/data/auth_repository.dart
class AuthRepository {
  AuthRepository(this._db);

  final AppDatabase _db;

  Future<User> login(String email, String password) async { ... }
}

// shared/providers/auth_repository_provider.dart
@Riverpod(keepAlive: true)
AuthRepository authRepository(Ref ref) {
  return AuthRepository(ref.watch(databaseProvider));
}

// 테스트 — abstract class 없이 Fake 주입
final container = ProviderContainer(overrides: [
  authRepositoryProvider.overrideWithValue(FakeAuthRepository()),
]);
```

구현체가 여러 개가 되는 경우(네트워크 + 로컬 캐시, 환경 분리 등) — 그때 abstract class로 계약을 추가한다.

```dart
// 구현체 교체가 실제로 필요해진 시점에 추가
abstract class AuthRepository {
  Future<User> login(String email, String password);
}

class RemoteAuthRepository implements AuthRepository { ... }
class CachedAuthRepository implements AuthRepository { ... }
```

---

## 상태 관리 (Riverpod)

기본은 `AsyncValue`를 사용한다. 도메인 고유 상태가 필요한 경우에만 `sealed class`로 정의한다.

### 기본 — AsyncValue

데이터 로딩, CRUD 결과 등 loading/error/data로 충분한 경우.

```dart
// features/flow/presentation/providers/flow_list_provider.dart
@riverpod
Stream<List<Flow>> flowList(Ref ref) {
  return ref.watch(flowRepositoryProvider).watchAll();
}

// 화면에서 .when()으로 분기
ref.watch(flowListProvider).when(
  data: (flows) => FlowListView(flows),
  loading: () => const CircularProgressIndicator(),
  error: (e, _) => ErrorView(e.toString()),
);
```

### 예외 — sealed class

도메인 고유 상태가 있어 loading/error/data로 표현이 불충분한 경우.

```dart
// features/timer/domain/timer_state.dart
sealed class TimerState {}
class TimerIdle extends TimerState {}
class TimerRunning extends TimerState {
  final Duration elapsed;
  TimerRunning(this.elapsed);
}
class TimerPaused extends TimerState {
  final Duration elapsed;
  TimerPaused(this.elapsed);
}
class TimerFinished extends TimerState {}

// features/timer/presentation/providers/timer_provider.dart
@riverpod
class TimerNotifier extends _$TimerNotifier {
  @override
  TimerState build() => TimerIdle();

  void start() => state = TimerRunning(Duration.zero);
  void pause() => state = TimerPaused((state as TimerRunning).elapsed);
  void finish() => state = TimerFinished();
}

// 화면에서 switch로 분기
return switch (ref.watch(timerNotifierProvider)) {
  TimerIdle()               => StartButton(),
  TimerRunning(:final elapsed) => TimerDisplay(elapsed),
  TimerPaused(:final elapsed)  => ResumeButton(elapsed),
  TimerFinished()           => CompletionView(),
};
```

---

## 슬라이스 간 통신

### 데이터 요청 — 계약 + Provider

```dart
// shared/contracts/i_user_provider.dart
abstract class IUserProvider {
  Future<UserSummary> getCurrentUser();
}

// features/auth/shared/auth_user_provider.dart
class AuthUserProvider implements IUserProvider {
  final AuthRepository _repo;
  AuthUserProvider(this._repo);

  @override
  Future<UserSummary> getCurrentUser() async {
    final user = await _repo.getCurrentUser();
    return UserSummary(id: user.id, name: user.name, avatarUrl: user.avatarUrl);
  }
}

// shared/contracts/i_user_provider_provider.dart
@Riverpod(keepAlive: true)
IUserProvider userProvider(Ref ref) {
  return AuthUserProvider(ref.watch(authRepositoryProvider));
}

// features/product/list/product_list_notifier.dart
// — 계약만 앎, auth 내부 구조 모름
final userProvider = ref.read(userProviderProvider);
final user = await userProvider.getCurrentUser();
```

### 이벤트 전파 — ref.listen + StateNotifier

EventBus(Static StreamController)는 Riverpod 환경에서 비권장. Riverpod 내장 메커니즘으로 대체한다.

```dart
// shared/providers/app_event_provider.dart
sealed class AppEvent {}
class UserLoggedIn extends AppEvent {
  final String userId;
  UserLoggedIn(this.userId);
}

@Riverpod(keepAlive: true)
class AppEventNotifier extends _$AppEventNotifier {
  @override
  AppEvent? build() => null;

  void emit(AppEvent event) => state = event;
}

// 발신 — features/auth/presentation/providers/auth_provider.dart
ref.read(appEventNotifierProvider.notifier).emit(UserLoggedIn(user.id));

// 수신 — features/cart/presentation/providers/cart_provider.dart
@override
CartState build() {
  ref.listen(appEventNotifierProvider, (_, event) {
    if (event is UserLoggedIn) clearCart();
  });
  return const CartEmpty();
}
```

### 화면 이동 — GoRouter 경로

```dart
// app/router/app_router.dart
final router = GoRouter(routes: [
  GoRoute(path: '/login', builder: (_, __) => const LoginPage()),
  GoRoute(path: '/products', builder: (_, __) => const ProductListPage()),
  GoRoute(
    path: '/products/:id',
    builder: (_, state) =>
      ProductDetailPage(id: state.pathParameters['id']!),
  ),
]);

// 슬라이스에서 — 경로 문자열만 앎
// ✔ ProductDetailPage 직접 import 금지
context.push('/products/${product.id}');
```

---

## Cross-cutting Concerns

```dart
// 로깅 — ProviderObserver (슬라이스 코드 수정 없음)
class AppObserver extends ProviderObserver {
  @override
  void didUpdateProvider(
    ProviderBase provider, Object? prev, Object? next, ProviderContainer container,
  ) {
    if (next is AsyncError) {
      debugPrint('[ERROR] ${provider.name}: ${next.error}');
    }
  }
}

void main() {
  runApp(ProviderScope(observers: [AppObserver()], child: const MyApp()));
}

// 네트워크 에러 — Dio Interceptor
class ErrorInterceptor extends Interceptor {
  @override
  void onError(DioException e, ErrorInterceptorHandler handler) {
    if (e.response?.statusCode == 401) {
      EventBus.emit(UserLoggedOut());
    }
    handler.next(e);
  }
}

// 에러 상태 — AsyncValue (Riverpod 내장)
// FutureProvider / AsyncNotifier 사용 시 자동으로 loading/error/data 분기
ref.watch(productListProvider).when(
  data: (products) => ProductListView(products),
  loading: () => const LoadingIndicator(),
  error: (e, _) => ErrorView(e.toString()),
);
```

---

## 테스트

```
단위 테스트: flutter_test + Fake (ProviderContainer.overrides)
E2E:         integration_test (Flutter 공식 E2E)

test/
  fakes/
    fake_auth_repository.dart
  features/auth/login/
    login_notifier_test.dart

integration_test/
  auth_flow_test.dart     ← E2E
  product_flow_test.dart
```

```dart
// Fake — Mock 대신
class FakeAuthRepository implements AuthRepository {
  final _users = <String, User>{};

  @override
  Future<User> login(String email, String password) async {
    final user = _users[email];
    if (user == null) throw AuthException.invalidCredentials();
    return user;
  }

  void addUser(String email, User user) => _users[email] = user;
}

// 테스트 — ProviderContainer.overrides로 Fake 주입
test('로그인 성공 시 LoginSuccess 상태', () async {
  final fakeRepo = FakeAuthRepository();
  fakeRepo.addUser('test@test.com', User(id: '1', email: 'test@test.com'));

  final container = ProviderContainer(overrides: [
    authRepositoryProvider.overrideWithValue(fakeRepo),
  ]);
  addTearDown(container.dispose);

  await container.read(loginNotifierProvider.notifier)
    .login('test@test.com', 'password');

  expect(
    container.read(loginNotifierProvider),
    isA<LoginSuccess>(),
  );
});
```

---

## 네이밍 컨벤션

| 항목        | 규칙                             | 예시                            |
| ----------- | -------------------------------- | ------------------------------- |
| 파일명      | snake_case                       | `login_page.dart`               |
| 폴더명      | snake_case                       | `features/auth/login/`          |
| 클래스      | PascalCase                       | `class LoginPage`               |
| 인터페이스  | abstract class + 선택적 i\_      | `abstract class AuthRepository` |
| 변수/함수   | lowerCamelCase                   | `Future<void> loadProducts()`   |
| 상수        | lowerCamelCase (Dart 표준)       | `const maxRetryCount = 3`       |
| Provider    | lowerCamelCase + Provider 접미사 | `final authRepositoryProvider`  |
| Fake        | fake\_ 접두사                    | `fake_auth_repository.dart`     |
| 테스트      | \_test 접미사                    | `login_notifier_test.dart`      |
| shared 모델 | _\_summary, _\_info              | `user_summary.dart`             |

### 좋은 이름 vs 나쁜 이름

```
✔ login_page.dart         — 도메인 + 역할 명확
✔ auth_repository.dart    — 도메인 + 역할 명확
✔ user_summary.dart       — 최소 공유 모델임이 드러남

✘ auth.dart               — 뭔지 모름
✘ helper.dart             — 쓰레기통 냄새
✘ login_response.dart     — shared에 있으면 안 됨 (슬라이스 내부로)
```
