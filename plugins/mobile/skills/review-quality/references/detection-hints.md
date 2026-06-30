# 스택 감지 + 항목별 코드 점검 단서

코드 검토를 "실행"하기 위한 작업 가이드. 두 부분으로 나뉜다.
1. **스택 감지** — 어떤 플랫폼/프레임워크인지 파일 신호로 판별
2. **항목별 점검 단서** — 각 품질 항목을 코드에서 어떻게 확인하는가 (grep 패턴·파일 위치)

검토는 "보이는 신호로 확인 가능한 것"만 단정한다. 코드만으로 확인 불가한 항목(예: 실제 60fps,
실제 시작 시간)은 단정하지 말고 "정적 분석으로 확인 불가 — 런타임 측정 권장"으로 분류한다.

---

## 1. 스택 감지

루트에서 아래 신호를 찾아 플랫폼을 정한다. 하이브리드(RN/Flutter/Tauri)는 네이티브 폴더가
함께 있으므로 **여러 플랫폼이 동시에 잡힐 수 있다** — 잡힌 플랫폼 전부를 검토 대상으로 삼는다.

| 플랫폼/프레임워크 | 감지 신호 |
|---|---|
| Android 네이티브 | `**/build.gradle`, `**/build.gradle.kts`, `**/AndroidManifest.xml`, `*.kt` / `*.java` |
| iOS 네이티브 | `*.xcodeproj`, `*.xcworkspace`, `**/Info.plist`, `*.swift`, `Podfile` |
| React Native | `package.json`에 `react-native` 의존성 + `android/` & `ios/` 폴더 동시 존재 |
| Flutter | `pubspec.yaml`, `lib/**/*.dart`, `android/` & `ios/` 동반 |
| Tauri | `src-tauri/`, `tauri.conf.json` (+ `gen/android`, `gen/apple` 있으면 모바일 타깃) |
| Capacitor | `capacitor.config.ts` / `.json`, `android/` & `ios/` |
| Cordova | `config.xml`, `platforms/` |

**판별 후 적용 규칙**
- Android 신호만 → Android 항목(UX/FN/PS/SEC/STORE)만 적용
- iOS 신호만 → Apple 대응 항목만 적용
- 둘 다(하이브리드) → **양쪽 모두** 적용하되, 하이브리드는 네이티브 설정이 자동 생성(gen/, ios/, android/)되는 경우가 많으니 "생성물 vs 직접 작성"을 구분해 본다
- 어느 신호도 없으면 → 사용자에게 대상 플랫폼을 확인

---

## 2. Android 점검 단서

대상 파일: `AndroidManifest.xml`, `build.gradle(.kts)`, `*.kt` / `*.java`, `res/`

| 항목 | 점검 단서 (grep/확인 포인트) |
|---|---|
| PS-6 Target_SDK | `targetSdk` / `targetSdkVersion` 값이 최신 안정 버전인지 |
| PS-7 Compile_SDK | `compileSdk` / `compileSdkVersion` 값 |
| PS-10 Production_Build | `debugImplementation` 라이브러리가 release에 새지 않는지, `isDebuggable` |
| SEC-1/2 권한 | `AndroidManifest.xml`의 `uses-permission` 목록 — 위치/SMS/통화/연락처 등 민감 권한 과다 여부 |
| SEC-3 Runtime_Permissions | `requestPermissions` / `ActivityResultContracts.RequestPermission` 호출 시점이 기능 진입부인지, `onCreate` 일괄 요청인지 |
| SEC-7 Sensitive_Logging | `Log.d/v/i/e(...)` 에 토큰·비밀번호·개인정보 변수 직접 출력 |
| SEC-8 Hardware_IDs | `getDeviceId`, `IMEI`, `Settings.Secure.ANDROID_ID`, `Build.SERIAL` 식별 목적 사용 |
| SEC-6 allowBackup | `AndroidManifest.xml`에 `android:allowBackup` 미설정(기본 true) → 토큰 등 민감 데이터가 ADB/클라우드 백업에 포함. `allowBackup="false"` 또는 백업 규칙에서 토큰 제외 여부 |
| SEC-12 Component_Export | `<activity/service/receiver/provider>`에 `android:exported` 누락 (특히 intent-filter 있는데 명시 안 됨) |
| SEC-14 Component_Protection | 공유 컴포넌트에 `android:protectionLevel="signature"` 여부 |
| SEC-15/16 Network | `usesCleartextTraffic="true"`, `network_security_config.xml` 존재·내용, `http://` 하드코딩 |
| SEC-18/19 WebView | `setAllowUniversalAccessFromFileURLs`, `addJavaScriptInterface`, `setJavaScriptEnabled` + 신뢰 불가 URL |
| SEC-20 App_Bundles | `DexClassLoader` / 외부 코드 동적 로드, AAB 빌드 여부 |
| UX-10 Theme | `values-night/`, `DayNight` 테마, `isLightTheme` 대응 |
| UX-16 Touch_Target | 클릭 가능한 뷰의 `minWidth/minHeight` < 48dp |
| UX-18 Content_Description | `ImageButton`/`ImageView` 등에 `contentDescription` 누락 |
| FN-9 Sharesheet | 커스텀 공유 UI 대신 `Intent.createChooser` 사용 여부 |
| PS-4 ANR | UI 스레드(메인)에서 네트워크/DB/파일 동기 호출 |

## 3. iOS / Apple 점검 단서

대상 파일: `Info.plist`, `*.entitlements`, `*.swift`, `project.pbxproj`, `Podfile`

| 항목 | 점검 단서 |
|---|---|
| SEC-4 Purpose Strings | 권한 사용하는데 `Info.plist`에 대응 `NS…UsageDescription` 누락 (카메라/위치/Face ID 등). **누락 시 런타임 크래시 + 리젝** |
| SEC-15/16 ATS | `NSAppTransportSecurity` → `NSAllowsArbitraryLoads = true` (전체 평문 허용은 리젝 위험), exception 도메인 범위 |
| SEC-1/2 권한 | 사용 프레임워크(CoreLocation, Contacts, HealthKit 등) 대비 과다 요청 |
| SEC-6 Data Protection | 민감 데이터를 `UserDefaults`에 저장(평문) vs Keychain/Data Protection 사용 |
| SEC-11 Biometric | `LAContext` 사용 시 `NSFaceIDUsageDescription` 동반 여부 |
| PS-10 릴리스 엔타이틀먼트 | `*.entitlements`의 `aps-environment=development`가 release에 남는지 등 서명/푸시 환경 누수. Xcode 아카이브가 production으로 덮는지 빌드 파이프라인 확인 필요(→ "의심"으로 분류) |
| PS-9 Non-public API | private API 심볼·`dlopen`/`performSelector`로 우회 호출 흔적 |
| SEC-20 No code download | 원격 JS/실행코드 다운로드 후 평가 (ARG 2.5.2 위반) |
| UX-10 Dark Mode | `UIUserInterfaceStyle` 강제 Light 고정 여부, semantic color 사용 |
| UX-16 Touch_Target | 탭 가능한 요소 frame < 44×44pt |
| UX-18 Accessibility | `accessibilityLabel` 누락, 이미지 버튼 미라벨 |
| FN-7 HEVC | 비디오 인코딩 코덱 |
| HEALTH-1~4 | HealthKit 데이터 iCloud 동기화·광고 SDK 동반 여부 |

## 4. 하이브리드(RN/Flutter/Tauri/Capacitor) 추가 단서

하이브리드는 **JS/Dart 레이어 + 네이티브 두 폴더**를 모두 본다.

| 확인 | 위치 |
|---|---|
| 네트워크 평문 | JS의 `http://` 하드코딩, `android/.../network_security_config`, iOS ATS |
| 권한 | RN: `react-native-permissions` 설정 + 양 네이티브 매니페스트/plist 동기화 여부 |
| 시크릿 노출 **[SEC-22]** | `.env`, JS 번들에 API 키·OAuth 클라이언트 시크릿 하드코딩. `VITE_*_SECRET` 등 빌드 타임 인라인 변수는 번들에 박혀 추출 가능 — 공개 클라이언트는 PKCE-only, 시크릿 교환은 백엔드로 위임 |
| WebView (Tauri/Capacitor) **[SEC-18/19]** | `tauri.conf.json`의 `csp`(null이면 XSS 방어 계층 없음)·allowlist, `dangerousRemoteDomainIpcAccess`, Capacitor `server.url` 원격 로드 |
| 다크모드 | 공통 UI 레이어의 테마 토큰이 OS 테마를 따르는지 |
| 터치영역/대비 **[UX-16/17]** | 하이브리드는 Tailwind/CSS로 렌더되어 dp/pt를 정적 단정 불가 → **"확인 불가(런타임)"로 분류**(§5), 네이티브 minWidth/minHeight 기준을 억지 적용하지 않는다 |

## 5. 정적 분석으로 확인 불가 → 런타임 측정 권장 항목

코드만 봐서 단정하면 안 되는 항목. 검토 결과에 "확인 불가(런타임)"로 표기한다.

- PS-1 실제 시작 시간(2초) / PS-2 실제 60fps / PS-11 실제 배터리 영향 → Xcode Organizer·MetricKit·Android vitals·Macrobenchmark
- UX-2~4 실제 생명주기 일시중지/재개 동작 → 기기 테스트
- STORE-* 스토어 등재물(스크린샷·등급) → 스토어 콘솔에서 확인
