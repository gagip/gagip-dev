# firebase

로컬에 설치된 Firebase CLI가 내장한 MCP 서버를, **읽기 전용 Crashlytics 도구 4개**로만 좁혀 붙인다.

## 붙는 도구

| 도구 | 하는 일 |
|---|---|
| `crashlytics_list_events` | 최근 크래시 이벤트 목록 (필터·개수 지정 가능) |
| `crashlytics_get_issue` | 이슈 하나의 상세 |
| `crashlytics_get_report` | 이벤트 수·영향 사용자 수 집계 리포트 |
| `crashlytics_list_notes` | 이슈에 달린 노트 목록 |

이슈 상태 변경(`crashlytics_update_issue`)과 노트 작성·삭제는 **일부러 빼 두었다.** 조회만 하려던 세션이 대시보드 상태를 바꾸는 사고를 구조적으로 막기 위해서다. 필요해지면 `.mcp.json`의 `--tools` 목록에 이름을 더한다.

Firestore·Authentication·Hosting·Remote Config·FCM 도구도 Firebase CLI에는 있지만 이 플러그인은 싣지 않는다. 같은 방식으로 `--tools`에 추가하거나 `--only <기능>`으로 묶음 단위 노출로 바꿀 수 있다.

## 스킬

| 스킬 | 설명 | 트리거 예시 |
|---|---|---|
| `crash-triage` | 상위 크래시를 스택·코드 대조로 원인까지 짚고, 기존 이슈인지 신규 후보인지 판정해 보고 | "크래시 확인해줘" |

위 도구가 붙어 있어야 동작한다. 조사와 판정까지만 하고 이슈 생성·코드 수정은 하지 않는다.

## 전제

- `firebase` 명령이 PATH에 있어야 한다 (`npm i -g firebase-tools`). 버전을 고정하려고 `npx ... @latest`가 아니라 설치된 CLI를 직접 부른다.
- `firebase login`이 되어 있어야 한다. 이 플러그인은 도구를 좁히느라 `firebase_login` 도구를 싣지 않으므로, 로그인은 터미널에서 미리 해 둔다.

## 쓰는 법

모든 Crashlytics 도구는 **앱 ID를 호출 인자로 받는다** (`1:000000000000:android:0000000000000000` 형태). 서버 설정에 프로젝트를 박아 두는 구조가 아니다.

앱 ID는 대개 프로젝트 안에 이미 있다.

- Android: `google-services.json` 의 `client[].client_info.mobilesdk_app_id`
- iOS: `GoogleService-Info.plist` 의 `GOOGLE_APP_ID`

## 붙이고 떼기

이 플러그인은 필요한 프로젝트에만 붙이는 것을 전제로 한다. 모든 세션에 상시 올리면 쓰지 않는 도구가 계속 실린다.

```bash
claude plugin install firebase@gagip-dev -s local
claude plugin disable firebase@gagip-dev
```
