---
name: review-quality
description: >
  모바일 앱 코드베이스를 플랫폼 공식 품질 기준(Android Core App Quality + Apple
  App Review Guidelines/HIG)에 비춰 정적 검토하고, 위반·미흡 항목을 근거와 함께
  리포트한다. 사용자가 "앱 품질 검토", "출시 전 점검", "스토어 심사 전 확인",
  "Play/App Store 리젝 위험 봐줘", "플랫폼 가이드라인 위반 확인", "Core App Quality",
  "App Review Guidelines", "권한/네트워크 보안 점검", "접근성/다크모드 점검",
  "이 앱 심사 통과될까", "Wear OS 품질", "워치 앱 출시 점검", "Wear App Quality" 같은 요청을 하면 반드시 사용한다. 특정 코드 로직 버그를 찾는
  일반 코드 리뷰가 아니라, "플랫폼이 요구하는 출시 품질 기준" 관점의 점검이다.
  Android·iOS 네이티브와 React Native·Flutter·Tauri·Capacitor 하이브리드, 그리고
  Wear OS(워치) 앱을 모두 다룬다.
argument-hint: "[검토할 앱 경로 (선택, 비우면 현재 위치)]"
allowed-tools: Bash, Read, Glob, Grep
---

## 입력

```
$ARGUMENTS
```

## 이 스킬이 하는 일

일반 코드 리뷰(로직 버그·가독성)가 아니라 **"플랫폼이 출시에 요구하는 품질 기준"** 관점의 검토다.
판단 근거는 플랫폼 공식 문서다 — Android Core App Quality, Apple App Review
Guidelines(ARG)/Human Interface Guidelines(HIG), 그리고 워치 앱은 Wear OS App Quality.
Android↔Apple을 1:1로 이어둔 매핑 표와 Wear OS 전용 항목(WO-*)이 자산으로 있어,
지적할 때마다 **어느 기준에 걸리는지 근거를 인용**한다. 그래야 "왜 고쳐야 하는지"가 명확해지고,
스토어 리젝 리스크인지 권고사항인지 구분된다.

## Step 1 — 검토 대상 결정

- `$ARGUMENTS`에 경로가 있으면 그 경로를, 없으면 현재 작업 디렉터리를 루트로 삼는다.
- 너무 크면(모노레포 등) 사용자에게 어느 앱/모듈을 볼지 먼저 확인한다.
- **비대화형 실행(서브에이전트·CI 등 사용자에게 물을 수 없는 환경)이면** 묻지 말고, 앱 엔트리
  (매니페스트·`tauri.conf.json`·`Info.plist`·앱 `package.json`)가 있는 주 패키지를 대상으로 고른 뒤,
  "물을 수 없어 ○○를 기본 대상으로 정함"을 리포트 첫머리에 명시한다. 검토가 멈추지 않게 하기 위함이다.

## Step 2 — 스택 감지

`references/detection-hints.md`의 **§1 스택 감지**를 읽고, 루트의 파일 신호로 플랫폼을 판별한다.
하이브리드(RN/Flutter/Tauri/Capacitor)는 네이티브 폴더가 함께 있어 **여러 플랫폼이 동시에 잡힐 수
있다** — 잡힌 플랫폼 전부를 대상으로 한다. 어느 신호도 없으면 사용자에게 대상 플랫폼을 확인한다.

Android 신호에 워치 신호(`android.hardware.type.watch`, `androidx.wear.*` 등)가 함께 잡히면
**Wear OS 앱**이다 — Android 항목에 더해 Wear OS 항목(WO-*)을 적용한다.

감지 결과를 한 줄로 먼저 보고한다. 예: "감지: React Native (android/ + ios/ 동반) → Android·Apple 양쪽 점검",
"감지: Wear OS 앱 (Jetpack Compose for Wear OS) → Android + Wear OS(WO-*) 점검".

## Step 3 — 해당 플랫폼 항목 점검

감지된 플랫폼에 맞는 항목만 점검한다 — 해당 없는 플랫폼 항목으로 노이즈를 내지 않는다.

1. `references/detection-hints.md`의 플랫폼별 §2~§4 점검 단서로 코드를 확인한다
   (grep 패턴·파일 위치가 정리돼 있다). `AndroidManifest.xml`, `Info.plist`, `build.gradle`,
   `tauri.conf.json` 같은 설정 파일이 가장 밀도 높은 신호원이니 먼저 본다.
2. 각 지적의 근거(Android 항목 ID / Apple 조항)는 `references/quality-map.md`에서 찾아 인용한다.
3. **확인의 강도를 구분한다** — 이게 이 검토의 신뢰도를 좌우한다:
   - **확정**: 코드/설정에 명확한 위반 신호가 있음 (예: `exported` 누락, ATS 전체 허용, 권한 일괄 요청)
   - **의심**: 신호는 있으나 맥락에 따라 정당할 수 있음 (예: 민감 권한이 핵심 기능과 연결됐을 수도)
   - **확인 불가(런타임)**: 코드만으로 단정 못 함 (실제 시작 시간·60fps·배터리 등).
     `detection-hints.md` §5 목록에 해당하면 측정 도구를 함께 안내한다.
4. **생체신호(ECG·심박·수면 등) 헬스 데이터를 다루는 앱이면** `quality-map.md` §6과 HEALTH-* 항목을
   추가로 본다. 사용자 노출 문구가 "정확/진단/위험도"처럼 의료기기 라인을 넘을 소지가 보이면, 품질
   검토 범위를 넘는 **규제 리스크로 에스컬레이션**한다(여기서 단정하지 않는다).
5. **Wear OS(워치) 앱이면** `quality-map.md` §7과 WO-* 항목을 §1~5 Android 항목에 **더해** 본다
   (`detection-hints.md` §2-1의 Wear 점검 단서 사용). WO-* 는 적용 대상이 3분류다 —
   **[모든 Wear 앱]**은 확정/의심으로 판정하고, **[Watch Face 전용]**은 Watch Face 신호
   (`watch_face_shapes.xml`·Watch Face Format XML·`WatchFaceService`)가 **없으면 "해당 없음"으로
   분류**해 지적하지 않는다(노이즈 방지), **[스토어/런타임]**은 "확인 불가"로 분류한다.

## 출력 형식

심각도 순으로 정리한다. 각 지적은 **무엇을·어디서·왜(근거)·어떻게**가 한눈에 보여야 한다.

```
# 모바일 앱 품질 검토 — <앱 이름/경로>

**감지된 스택**: <플랫폼들>
**점검 범위**: <적용한 카테고리들> (해당 없는 플랫폼 항목 제외)

## 🔴 리젝 위험 / 위반 (확정)
- **[SEC-12] exported 누락** — `AndroidManifest.xml:42` `<service>`에 intent-filter가 있으나 `android:exported` 미명시
  - 근거: Android SEC-12(Component_Export). iOS는 샌드박스가 흡수 → 해당 없음.
  - 수정: `android:exported="false"` 명시 (외부 호출 불필요 시).

## 🟡 권고 / 개선 (의심·HIG 권고)
- ...

## ⚪ 확인 불가 (런타임 측정 필요)
- **[PS-1] 시작 시간** — 정적 분석으로 확인 불가. Xcode Organizer(Launch Time)·Android vitals로 측정 권장.

## 📋 점검 요약표
| 카테고리 | 점검 | 확정 위반 | 권고 | 확인 불가 |
|---|---|---|---|---|
| UX | n | n | n | n |
| ... | | | | |
```

## 종료 [STOP]

리포트를 출력한 뒤 **여기서 멈춘다 — 코드를 수정하지 않는다.** 이 스킬은 진단 전용이다.
사용자가 수정을 원하면 별도로 요청하게 한다(어떤 지적을 고칠지 사용자가 고르도록).

## 원칙

- **근거 없는 지적 금지.** 모든 지적은 `quality-map.md`의 항목 ID/조항으로 근거를 단다. 근거를 못 대면
  그건 이 스킬의 검토 범위가 아니다(일반 코드 리뷰로 돌린다).
- **해당 없는 플랫폼 항목으로 노이즈 내지 않기.** iOS 앱에 `exported` 지적, Android 앱에 ATS 지적은
  무의미하다. 감지된 플랫폼에 매핑되는 항목만 적용한다.
- **단정과 추정을 섞지 않기.** "확정/의심/확인 불가"를 명확히 갈라야 리포트가 신뢰를 얻는다.
