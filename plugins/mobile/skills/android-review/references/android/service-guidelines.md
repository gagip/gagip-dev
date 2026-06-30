# Android Service 가이드라인

백그라운드 서비스 관련 리뷰 기준. 공식 문서(developer.android.com) 기반.

---

## 1. 서비스 타입 선택

작업 성격에 따라 선택한다.

| 상황 | 선택 |
|------|------|
| 사용자가 인지해야 하거나 중단 시 UX 손상이 심각한 작업 (오디오 재생, 내비게이션) | Foreground Service |
| 지연 가능하고 앱 종료 후에도 완료되어야 하는 작업 (동기화, 업로드) | WorkManager |
| 짧고 앱이 살아있는 동안만 실행되는 작업 | 코루틴 |

> 공식 문서: *"In many cases, using WorkManager is preferable to using foreground services directly."*

**리뷰 체크포인트**
- Foreground Service가 WorkManager로 대체 가능한 작업을 처리하고 있지는 않은가?
- 단순 비동기 작업에 Service를 사용하고 있지는 않은가?

---

## 2. Foreground Service

### Manifest 선언

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<!-- Android 14+: 타입별 권한 추가 (사용하는 타입만) -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK" />

<service
    android:name=".MyForegroundService"
    android:foregroundServiceType="mediaPlayback"
    android:exported="false" />
```

### foregroundServiceType 선택 기준

| 타입 | 런타임 권한 필요 | 용도 |
|------|---------------|------|
| `mediaPlayback` | 없음 | 오디오/비디오 재생 |
| `location` | `ACCESS_FINE_LOCATION` | 내비게이션, 위치 공유 |
| `camera` | `CAMERA` | 백그라운드 카메라 |
| `microphone` | `RECORD_AUDIO` | 음성 녹음, 통화 |
| `dataSync` | 없음 | 업로드/다운로드/백업 |
| `health` | `BODY_SENSORS` 등 | 피트니스/건강 모니터링 |
| `shortService` | 없음 | 짧은 긴급 작업 (~3분 타임아웃) |

### startForeground() 호출 타이밍

`startForegroundService()` 호출 후 **5초 이내**에 `startForeground()`를 호출해야 한다. 초과 시 ANR 및 시스템 강제 종료.

```kotlin
override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    try {
        ServiceCompat.startForeground(
            this,
            NOTIFICATION_ID,  // 0이 아닌 양수
            buildNotification(),
            ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK
        )
    } catch (e: ForegroundServiceStartNotAllowedException) {
        // Android 12+: 백그라운드에서 시작 불가 — WorkManager로 대체
        return START_NOT_STICKY
    }
    return START_STICKY
}
```

`ServiceCompat.startForeground()`를 사용하면 API 레벨별 호환성이 자동 처리된다.

### 알림 채널

Android 8+에서 알림 채널 생성 없이 알림을 띄우면 크래시가 발생한다.

```kotlin
private fun createNotificationChannel() {
    val channel = NotificationChannel(
        CHANNEL_ID,
        "재생 서비스",
        NotificationManager.IMPORTANCE_LOW  // 포그라운드 서비스는 LOW 이상 필수
    )
    getSystemService(NotificationManager::class.java)
        .createNotificationChannel(channel)
}
```

**리뷰 체크포인트**
- `foregroundServiceType`이 Manifest에 선언되어 있는가? (Android 14+)
- 사용하는 타입에 맞는 `FOREGROUND_SERVICE_*` 권한이 선언되어 있는가?
- `startForeground()` 호출이 `onStartCommand()` 최상단에 있는가?
- `ServiceCompat.startForeground()`를 사용하는가?
- 알림 채널이 `IMPORTANCE_LOW` 이상으로 설정되어 있는가?
- `ForegroundServiceStartNotAllowedException` 예외 처리가 있는가? (Android 12+)

---

## 3. onStartCommand() 반환값

| 반환값 | 재시작 여부 | Intent 재전달 | 사용 케이스 |
|--------|------------|--------------|-----------|
| `START_NOT_STICKY` | ❌ | ❌ | 실패해도 괜찮은 단순 작업 |
| `START_STICKY` | ✅ (null Intent) | ❌ | 지속 대기 서비스 (음악 플레이어) |
| `START_REDELIVER_INTENT` | ✅ | ✅ | 반드시 완료해야 하는 작업 (다운로드) |

```kotlin
// START_STICKY: Intent가 null로 재시작될 수 있음을 처리해야 함
override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    intent?.let { handleIntent(it) }  // null 처리 필수
    return START_STICKY
}
```

**리뷰 체크포인트**
- `START_STICKY` 사용 시 `intent`가 null인 경우를 처리하는가?
- 반드시 완료해야 하는 작업에 `START_NOT_STICKY`를 쓰고 있지 않은가?

---

## 4. 생명주기 — 리소스 정리

### stopSelf(startId) 사용

동시에 여러 요청이 들어왔을 때 안전하게 종료하려면 `stopSelf(startId)`를 사용한다.

```kotlin
// stopSelf(): 무조건 즉시 종료 — 다른 요청 처리 중에도 종료될 수 있어 위험
// stopSelf(startId): 해당 startId가 마지막 요청일 때만 종료 — 안전
override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    serviceScope.launch {
        try {
            performWork()
        } finally {
            stopSelf(startId)
        }
    }
    return START_REDELIVER_INTENT
}
```

### 코루틴 스코프 정리

```kotlin
class MyService : Service() {
    private val job = SupervisorJob()
    private val serviceScope = CoroutineScope(job + Dispatchers.IO)

    override fun onDestroy() {
        super.onDestroy()
        job.cancel()  // 모든 코루틴 취소
    }
}
```

**리뷰 체크포인트**
- 작업 완료 후 `stopSelf(startId)`를 호출하는가?
- `onDestroy()`에서 코루틴 스코프를 취소하는가?
- `onDestroy()`에서 `stopForeground(STOP_FOREGROUND_REMOVE)`를 호출하는가?

---

## 5. 권한 및 버전별 제약

### Android 버전별 주요 변경사항

| 버전 | 변경사항 |
|------|---------|
| Android 8 (API 26) | 백그라운드 Service 실행 제한, 알림 채널 필수 |
| Android 9 (API 28) | `FOREGROUND_SERVICE` 권한 필수 |
| Android 12 (API 31) | 백그라운드에서 FGS 시작 불가 (`ForegroundServiceStartNotAllowedException`) |
| Android 14 (API 34) | 모든 FGS에 `foregroundServiceType` 선언 필수, 타입별 권한 필수 |
| Android 15 (API 35) | `dataSync`, `mediaProcessing` 타임아웃 제한 추가 |

### Android 8+ 백그라운드 실행 제한

```kotlin
// ❌ 앱이 백그라운드에 있으면 무시됨 (API 26+)
startService(Intent(context, MyService::class.java))

// ✅ Foreground Service로 시작
context.startForegroundService(Intent(context, MyService::class.java))
```

**리뷰 체크포인트**
- Android 8+에서 `startService()` 대신 `startForegroundService()`를 사용하는가?
- `FOREGROUND_SERVICE` 권한이 Manifest에 선언되어 있는가?

---

## 6. Bound Service

같은 프로세스 내에서는 `Binder`를 직접 상속한다. 다른 프로세스(IPC)는 `Messenger` 또는 AIDL을 사용한다.

```kotlin
class PlayerService : Service() {

    inner class PlayerBinder : Binder() {
        fun getService(): PlayerService = this@PlayerService
    }

    private val binder = PlayerBinder()

    override fun onBind(intent: Intent): IBinder = binder

    override fun onUnbind(intent: Intent): Boolean {
        // 리소스 정리
        return true  // true 반환 시 재바인딩 때 onRebind() 호출됨
    }

    override fun onDestroy() {
        super.onDestroy()
        // 리소스 정리
    }
}
```

### 바인딩 생명주기

Activity에서 바인딩할 때는 `onStart()`/`onStop()` 쌍을 사용한다. `onResume()`/`onPause()`는 불필요한 리소스 소비를 일으킨다.

```kotlin
override fun onStart() {
    super.onStart()
    bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE)
}

override fun onStop() {
    super.onStop()
    if (isBound) {
        unbindService(serviceConnection)
        isBound = false
    }
}
```

**리뷰 체크포인트**
- `onServiceDisconnected()`에서 서비스 참조를 null로 처리하는가?
- 바인딩/언바인딩 쌍이 대칭을 이루는가?
- 같은 프로세스인데 AIDL을 사용하고 있지는 않은가?

---

## 7. Service ↔ Compose 통신

### 상태 노출: StateFlow

Service의 상태는 `StateFlow`로 노출하여 단방향 데이터 흐름을 유지한다.

```kotlin
class PlayerService : Service() {
    companion object {
        private val _state = MutableStateFlow(PlaybackState.IDLE)
        val state: StateFlow<PlaybackState> = _state.asStateFlow()
    }
}
```

### ServiceConnection 관리: ViewModel

`ServiceConnection`은 ViewModel에서 관리한다. Composable에서 직접 관리하면 recomposition 시 연결이 끊길 수 있다.

```kotlin
class PlayerViewModel(app: Application) : AndroidViewModel(app) {

    private var service: PlayerService? = null
    private var isBound = false

    private val connection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName, binder: IBinder) {
            service = (binder as PlayerService.PlayerBinder).getService()
            isBound = true
        }
        override fun onServiceDisconnected(name: ComponentName) {
            service = null
            isBound = false
        }
    }

    fun bind(context: Context) {
        context.bindService(
            Intent(context, PlayerService::class.java),
            connection,
            Context.BIND_AUTO_CREATE
        )
    }

    fun unbind(context: Context) {
        if (isBound) {
            context.unbindService(connection)
            isBound = false
        }
    }

    override fun onCleared() {
        super.onCleared()
        if (isBound) getApplication<Application>().unbindService(connection)
    }
}
```

### bind/unbind: DisposableEffect

```kotlin
@Composable
fun PlayerScreen(viewModel: PlayerViewModel = viewModel()) {
    val context = LocalContext.current

    DisposableEffect(context) {
        viewModel.bind(context)
        onDispose { viewModel.unbind(context) }  // Composable 이탈 시 반드시 정리
    }

    val state by PlayerService.state.collectAsStateWithLifecycle()
    // ...
}
```

**리뷰 체크포인트**
- `ServiceConnection`을 Composable이 아닌 ViewModel에서 관리하는가?
- `DisposableEffect`의 `onDispose`에서 `unbindService()`를 호출하는가?
- Service 상태가 `StateFlow`로 노출되어 있는가?
- Composable이 Service를 직접 참조하지 않는가?

---

## 간단 언급

**Hilt 주입** — Service에 `@AndroidEntryPoint` 선언, 필드는 `@Inject lateinit var` 패턴 사용. `kotlin-conventions.md` 참고.

**알림 딥링크** — 알림 탭 시 Compose Navigation으로 연결하려면 `PendingIntent`에 딥링크 URI를 담아 `NavDeepLinkBuilder`로 처리한다.
