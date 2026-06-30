# 모바일 앱 품질 매핑: Android Core App Quality ↔ Apple

이 문서는 검토에서 지적을 낼 때 **근거를 인용**하기 위한 레퍼런스다. 각 행은
"Android 품질 기준 1건 ↔ Apple 쪽 대응(심사 조항/디자인 가이드/플랫폼 메커니즘)"을 1:1로 잇는다.

## 출처 (정본)

- Android Core App Quality — https://developer.android.com/docs/quality-guidelines/core-app-quality
- Apple App Review Guidelines (ARG) — https://developer.apple.com/app-store/review/guidelines/
- Apple Human Interface Guidelines (HIG) — https://developer.apple.com/design/human-interface-guidelines/

## 범례

- **ARG x.y** = App Review Guidelines 조항 (심사에서 거부 사유가 되는 강제 규칙)
- **HIG: 섹션** = Human Interface Guidelines 권고 (디자인/UX 원칙)
- **FW/도구** = iOS 프레임워크·플랫폼 메커니즘 (문서가 아니라 코드로 충족)
- **정책** = App Store Connect 운영 정책
- `—` = Apple에 직접 대응 문서·조항이 없고 플랫폼 메커니즘으로 흡수됨

> 인용 형식 권장: "Android **UX-14**(터치 영역 48dp) ↔ Apple **HIG: Accessibility**(최소 44×44pt)".
> ID는 이 문서의 자체 부여 코드다(Android 공식 문서엔 항목 ID가 없다).

## 목차

1. UX — 사용자 환경 (UX-1 ~ UX-16)
2. FN — 기능 (FN-1 ~ FN-10)
3. PS — 성능·안정성 (PS-1 ~ PS-11)
4. SEC — 개인정보·보안 (SEC-1 ~ SEC-20)
5. STORE — 스토어 등재 (STORE-1 ~ STORE-6)
6. 헬스 데이터 추가 규제 (Voltera 등 생체신호 앱)

---

## 1. UX — 사용자 환경

| ID | Android 기준 | Apple 대응 | 종류 |
|---|---|---|---|
| UX-1 | Consistent_UX — 폼팩터 전반 일관된 경험 | HIG: Designing for iOS / iPadOS | HIG |
| UX-2 | App_Switcher — 포커스 전환 시 백그라운드, 복귀 시 포그라운드 복원 | App lifecycle (`scenePhase` / `UIScene`) | FW |
| UX-3 | Sleep_Resume — 절전 진입 시 일시중지, 해제 시 재개 | `scenePhase` background/inactive 처리 | FW |
| UX-4 | Lock_Resume — 잠금 시 일시중지, 해제 시 재개 | `scenePhase` 처리 | FW |
| UX-5 | Display_State_Parity — 방향/접힘 상태에서 동일 기능 | HIG: Multitasking, Layout | HIG |
| UX-6 | Fullscreen_Display — 레터박스 없이 창 채움 | HIG: Layout (Safe Area) + ARG 2.4.1 | HIG/ARG |
| UX-7 | Orientation_Transitions — 방향/접힘 빠른 전환 | HIG: Layout / Adaptivity (Size Classes) | HIG |
| UX-8 | Graphic_Quality — 왜곡·흐림·모자이크 없음 | HIG: Images + ARG 4.2 | HIG/ARG |
| UX-9 | Line_Length — 텍스트 줄 45~75자 | HIG: Typography (수치 규정은 없고 원칙만) | HIG |
| UX-10 | Theme_Support — 라이트/다크 테마 | HIG: Dark Mode (semantic colors) | HIG |
| UX-11 | Back_Button_Nav — 표준 뒤로가기 | HIG: Navigation (edge-swipe back) | HIG |
| UX-12 | Back_Gesture_Nav — 제스처 탐색 | HIG: Navigation / Gestures | HIG |
| UX-13 | State_Preservation — 종료 후 상태 복원 | State restoration (`NSUserActivity` / `@SceneStorage`) | FW |
| UX-14 | Notification_Quality — 유용한 알림, 프로모션 금지 | HIG: Notifications + ARG 4.5.4 | HIG/ARG |
| UX-15 | Conversation_Quality — MessagingStyle/바로답장 | Communication Notifications / Intents (iOS 15+) | FW |
| UX-16 | Touch_Target_Size — 최소 48dp | HIG: Accessibility (**최소 44×44 pt**, 수치 다름) | HIG |
| UX-17 | Visual_Contrast — 3:1 / 4.5:1 | HIG: Accessibility (Color and contrast, WCAG 동일) | HIG |
| UX-18 | Content_Description — 비텍스트 요소에 설명 | HIG: Accessibility — `accessibilityLabel` (VoiceOver) | HIG/FW |

> 메모: contentDescription ↔ accessibilityLabel, 48dp ↔ 44pt는 개념 대응이되 **수치가 다르다**.
> 줄 길이(UX-9)는 Apple이 자수를 못 박지 않으므로 "원칙 위반" 톤으로만 지적한다.

## 2. FN — 기능

| ID | Android 기준 | Apple 대응 | 종류 |
|---|---|---|---|
| FN-1 | Audio_Playback_Start — 1초 내 재생 또는 로딩 표시 | HIG: Loading / Playing audio | HIG |
| FN-2 | Audio_Focus_Request/Change — 오디오 포커스 | `AVAudioSession` (category·interruptions) | FW |
| FN-3 | Audio_Playback_Background — 백그라운드 재생 | Background Modes: Audio | FW |
| FN-4 | Audio_Notification_Style — MediaStyle 알림 | `MPNowPlayingInfoCenter` / Control Center | FW |
| FN-5 | Audio_Playback_Resume — 인터럽션 후 복귀 처리 | AVAudioSession interruption 콜백 | FW |
| FN-6 | Video_PiP — PiP 재생 | `AVPictureInPictureController` | FW |
| FN-7 | Video_Encoding — HEVC 사용 | HEVC 네이티브 지원 | FW |
| FN-8 | Video_Playback_Background — 백그라운드 동영상 | Background Modes / PiP | FW |
| FN-9 | System_Sharesheet — 시스템 공유 시트 사용 | `UIActivityViewController` / `ShareLink` | FW |
| FN-10 | Background_Service_Optimization — 불필요한 장시간 실행 금지 | `BGTaskScheduler` + ARG 2.5.4 | FW/ARG |

## 3. PS — 성능·안정성

| ID | Android 기준 | Apple 대응 | 종류 |
|---|---|---|---|
| PS-1 | App_Startup_Time — 빠른 로드/2초+ 시 진행표시 | MetricKit·Xcode Organizer(Launch Time) + HIG: Launching | FW/도구 |
| PS-2 | Rendering_Performance — 60fps(16ms) | Xcode Organizer(Hangs/Hitches), Instruments | 도구 |
| PS-3 | StrictMode_Compliance — 메인스레드 위반 없음 | Main Thread Checker / Thread Sanitizer | 도구 |
| PS-4 | Stability_ANR — UI 스레드 차단·크래시·ANR 없음 | Xcode Organizer(Hang Rate) + ARG 2.1 | 도구/ARG |
| PS-5 | Android_Platform_Compatibility — 최신 OS 무충돌 | ARG 2.4.x | ARG |
| PS-6 | Target_SDK_Version — 최신 SDK target | **최신 SDK 빌드 의무**(targetSdk 개념 없음, 빌드 SDK로 강제) | 정책 |
| PS-7 | Compile_SDK_Version — 최신 SDK compile | 최신 Xcode/SDK 빌드 요구 | 정책 |
| PS-8 | SDK_Maintenance — SDK 최신 유지 | iOS 17+ Privacy Manifest·서드파티 SDK 서명 | 정책 |
| PS-9 | Non_SDK_Interfaces — 비공개 API 금지 | **ARG 2.5.1 (public APIs only)** | ARG |
| PS-10 | Production_Build_Quality — 디버그 라이브러리 미포함, **릴리스 엔타이틀먼트/서명 환경 누수 없음**(예: iOS `aps-environment=development`가 release에 남으면 production 푸시 불가) | ARG 2.1 / 2.2 (베타는 TestFlight) | ARG |
| PS-11 | Power_Management — Doze/Standby 지원 | ARG 2.4.1 (efficient power) + MetricKit(Battery) | ARG/도구 |

## 4. SEC — 개인정보·보안

| ID | Android 기준 | Apple 대응 | 종류 |
|---|---|---|---|
| SEC-1 | Minimize_Permissions — 최소 권한 | ARG 5.1.1(ii) + HIG: Privacy | ARG/HIG |
| SEC-2 | Sensitive_Permissions — 위치/SMS/통화 등 | ARG 5.1.1, 5.1.5 (Location) | ARG |
| SEC-3 | Runtime_Permissions — 사용 시점 요청 | HIG: Privacy (just-in-time 권한) | HIG |
| SEC-4 | Permission_Rationale — 권한 사유 설명 | **Purpose strings** (`Info.plist` `NS…UsageDescription`) | FW/정책 |
| SEC-5 | Graceful_Degradation — 거부 시 대체 경로 | HIG: Privacy | HIG |
| SEC-6 | Sensitive_Data_Storage — 내부 저장 | **Data Protection API / Keychain** | FW |
| SEC-7 | Sensitive_Data_Logging — 민감정보 로깅 금지 | ARG 5.1.1, 5.1.2 | ARG |
| SEC-8 | Hardware_IDs — 영구 하드웨어 ID 금지 | ARG 5.1.1(iv) — IDFV/IDFA, no fingerprinting | ARG |
| SEC-9 | Autofill_Hints — 자동완성 힌트 | `textContentType` (AutoFill) | FW |
| SEC-10 | Credential_Manager — 패스키/제휴ID | Authentication Services / Passkeys / Sign in with Apple (ARG 4.8) | FW/ARG |
| SEC-11 | Biometric_Authentication — 생체 인증 | **LocalAuthentication** (Face ID/Touch ID; Face ID는 purpose string 필수) | FW |
| SEC-12 | Component_Export — exported 명시 | — (iOS 앱 샌드박스가 기본 차단) | 플랫폼 |
| SEC-13 | Component_Permissions — 안전한 컴포넌트 통신 | App Groups / URL Scheme 검증 | 플랫폼 |
| SEC-14 | Component_Protection — signature 권한 | — (샌드박스·entitlement로 대체) | 플랫폼 |
| SEC-15 | Network_Security_Traffic — 모든 트래픽 SSL | **App Transport Security (ATS)** | FW |
| SEC-16 | Network_Security_Configuration — 보안 구성 선언 | ATS exception keys (`Info.plist`) | FW |
| SEC-17 | Security_Provider_Initialization — 보안 제공자 초기화 | — (OS가 보안 스택 관리) | 플랫폼 |
| SEC-18 | WebView_Asset_Loader — 로컬 콘텐츠 안전 로딩 | `WKWebView` 로컬 로딩 베스트프랙티스 | FW |
| SEC-19 | WebView_JavaScript — 안전한 JS 브리지 | `WKScriptMessageHandler` | FW |
| SEC-20 | App_Bundles — 동적 코드 로드 금지 | **ARG 2.5.2 (self-contained, no executable code download)** | ARG |
| SEC-21 | Cryptographic_Algorithms — 플랫폼 제공 암호화 | **CryptoKit** (커스텀 알고리즘 지양) | FW |
| SEC-22 | (공통) Secret_In_Bundle — 공개 클라이언트(모바일/웹 번들)에 클라이언트 시크릿·API 키 비포함, OAuth는 PKCE 사용 | ARG 5.1.1 + 모바일 공개 클라이언트 베스트프랙티스(시크릿 교환은 백엔드 위임) | ARG/FW |

> 메모: SEC-12~14, SEC-17은 iOS 샌드박스 모델이 구조적으로 흡수한다. iOS 검토에서는
> "해당 없음(샌드박스가 처리)"으로 분류하고, 대신 entitlement·App Groups 오남용을 본다.
> 메모: SEC-6에는 Android `android:allowBackup` 미설정(기본 true)도 포함한다 — 평문 토큰이
> ADB/클라우드 백업으로 추출될 수 있어 민감 데이터 저장의 대표 증폭 요인이다.
> 메모: SEC-22는 Android Core App Quality에 단독 항목으로 있진 않지만(공통 보안 원칙), 번들은
> 추출·디컴파일되므로 양 플랫폼 공통으로 본다. `detection-hints.md` §4 "시크릿 노출"의 근거 ID다.

## 5. STORE — 스토어 등재

| ID | Android 기준 | Apple 대응 | 종류 |
|---|---|---|---|
| STORE-1 | Play_Content_Policies — 콘텐츠 정책/IP | ARG 1 (Safety), 5.2 (IP) | ARG |
| STORE-2 | Play_Content_Rating — 콘텐츠 등급 | App Store Connect 연령 등급(Age Rating) | 정책 |
| STORE-3 | Play_Feature_Graphic — 그래픽 사양 | ARG 2.3.10 + 스크린샷/프리뷰 사양 (feature graphic 없음) | ARG/정책 |
| STORE-4 | Play_Device_References — 타기기 표시 금지 | ARG 2.3.10 | ARG |
| STORE-5 | Play_Misleading_Content — 오해 소지 금지 | ARG 2.3 (Accurate Metadata) | ARG |
| STORE-6 | Play_User_Reviews — 리뷰 버그 대응 | ARG 1.1.x + App Store 리뷰 응답 | ARG/정책 |

## 6. 헬스 데이터 추가 규제 (생체신호 앱)

일반 품질 기준 위에 한 겹 더 있는 규제. Android Core App Quality에는 거의 없지만 Apple엔 명시 조항이 있다.
ECG·심박·수면 등 생체신호를 해석해 보여주는 앱(예: Voltera)이면 반드시 본다.

| ID | 기준 | Apple 근거 | 비고 |
|---|---|---|---|
| HEALTH-1 | 헬스 데이터 iCloud 저장 금지 | ARG 5.1.3 | |
| HEALTH-2 | 헬스 데이터 광고 활용 금지 | ARG 5.1.3 | HealthKit 정책과 중첩 |
| HEALTH-3 | 의료기기 정확성 주장 시 규제 준수 | ARG 5.1.3 | 웰니스/의료기기 경계 → 별도 분류 필요 |
| HEALTH-4 | 헬스 데이터 third-party 공유 금지 | HealthKit 정책 | |

> 문구가 "의료기기 라인"을 넘는지(예: "정확", "진단", "위험도")는 별도 규제 판별 영역이다.
> 코드 출력 문구·i18n에서 이런 표현이 보이면 품질 검토 범위를 넘는 규제 리스크로 **에스컬레이션**한다.
