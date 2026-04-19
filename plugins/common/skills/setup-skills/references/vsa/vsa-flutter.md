# VSA Flutter 아키텍처

> Flutter(Dart + Riverpod) 프로젝트에 적용되는 VSA 규칙.
> 공통 원칙은 `vsa-common-architecture.md` 참조.

---

## 폴더 구조

```
lib/
├── app/
│   ├── home/
│   │   ├── home_page.dart
│   │   └── home_notifier.dart
│   ├── router/
│   │   └── app_router.dart
│   └── di/
│       └── app_module.dart
│
├── features/
│   ├── auth/
│   │   ├── login/
│   │   │   ├── login_page.dart
│   │   │   ├── login_notifier.dart   (또는 login_cubit.dart)
│   │   │   ├── login_state.dart
│   │   │   └── login_provider.dart   ← Riverpod Provider
│   │   ├── register/
│   │   │   ├── register_page.dart
│   │   │   ├── register_notifier.dart
│   │   │   └── register_provider.dart
│   │   └── shared/                   ← register 생기면 생성
│   │       ├── auth_repository.dart        (abstract class)
│   │       ├── auth_repository_impl.dart
│   │       ├── auth_repository_provider.dart
│   │       ├── user_model.dart
│   │       └── auth_exception.dart
│   └── product/
│       ├── list/
│       ├── detail/
│       └── shared/
│           ├── product_repository.dart
│           └── product_model.dart
│
├── shared/
│   ├── contracts/
│   │   └── i_user_provider.dart
│   ├── models/
│   │   └── user_summary.dart
│   ├── events/
│   │   ├── app_event.dart
│   │   └── event_bus.dart
│   ├── network/
│   │   └── api_client.dart
│   └── utils/
│       └── validators.dart
│
└── main.dart
```

---

## 슬라이스 단위

**Page + Notifier(또는 Cubit) + State** 묶음

```
features/auth/login/
  login_page.dart      ← UI (ConsumerWidget)
  login_notifier.dart  ← 상태 + 로직
  login_state.dart     ← 상태 정의
  login_provider.dart  ← Riverpod Provider 정의
```

---

## Repository 패턴

```dart
// abstract class — 계약
// features/auth/shared/auth_repository.dart
abstract class AuthRepository {
  Future<User> login(String email, String password);
  Future<User> getCurrentUser();
}

// 구현체 — 피처군 shared 소유
// features/auth/shared/auth_repository_impl.dart
class AuthRepositoryImpl implements AuthRepository {
  final ApiClient _api;

  AuthRepositoryImpl(this._api);

  @override
  Future<User> login(String email, String password) async {
    final res = await _api.post('/auth/login', {
      'email': email,
      'password': password,
    });
    return User.fromJson(res);
  }
}

// Provider — 피처군 shared 소유
// features/auth/shared/auth_repository_provider.dart
@Riverpod(keepAlive: true)
AuthRepository authRepository(Ref ref) {
  final api = ref.watch(apiClientProvider);
  return AuthRepositoryImpl(api);
}
```

---

## 상태 관리 (Riverpod)

```dart
// login_state.dart
sealed class LoginState {
  const LoginState();
}

class LoginIdle extends LoginState { const LoginIdle(); }
class LoginLoading extends LoginState { const LoginLoading(); }
class LoginSuccess extends LoginState {
  final User user;
  const LoginSuccess(this.user);
}
class LoginError extends LoginState {
  final String message;
  const LoginError(this.message);
}

// login_notifier.dart
@riverpod
class LoginNotifier extends _$LoginNotifier {
  @override
  LoginState build() => const LoginIdle();

  Future<void> login(String email, String password) async {
    state = const LoginLoading();
    try {
      final repo = ref.read(authRepositoryProvider);
      final user = await repo.login(email, password);
      state = LoginSuccess(user);
    } on AuthException catch (e) {
      state = LoginError(e.message);
    }
  }
}

// login_page.dart — 상태 구독
class LoginPage extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(loginNotifierProvider);

    return switch (state) {
      LoginIdle() || LoginError() => _LoginForm(),
      LoginLoading()              => const LoadingIndicator(),
      LoginSuccess(:final user)   => _navigateToHome(user),
    };
  }
}
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

### 이벤트 전파 — EventBus (Stream)

```dart
// shared/events/app_event.dart
sealed class AppEvent {}

class UserLoggedIn extends AppEvent {
  final String userId;
  UserLoggedIn(this.userId);
}

class OrderCompleted extends AppEvent {
  final String orderId;
  OrderCompleted(this.orderId);
}

// shared/events/event_bus.dart
class EventBus {
  static final _controller = StreamController<AppEvent>.broadcast();
  static Stream<AppEvent> get stream => _controller.stream;
  static void emit(AppEvent event) => _controller.add(event);
}

// 발신 — features/auth/login/login_notifier.dart
EventBus.emit(UserLoggedIn(user.id));

// 수신 — features/cart/cart_notifier.dart
@override
CartState build() {
  ref.listen(
    Stream.fromFuture(Future.value(null)), // Riverpod stream 연결
    (_, __) {},
  );
  EventBus.stream
    .whereType<UserLoggedIn>()
    .listen((_) => clearCart());
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
