# android

Android 개발에 특화된 Claude Code 플러그인. 수직 슬라이스 아키텍처(VSA) 기반 프로젝트를 위한 스킬 모음.

## 스킬 목록

| 스킬          | 트리거 예시                                   |
| ------------- | --------------------------------------------- |
| `architect`   | "아키텍처 봐줘", "구조 리뷰해줘", "설계해줘" |
| `review-code` | "리뷰해줘", "코드 봐줘", "코드 점검"          |
| `write-test`  | "테스트 써줘", "단위 테스트 추가"             |

## 스킬 상세

### `architect`

수직 슬라이스 아키텍처(VSA) 기반으로 프로젝트를 피드백하거나 새 기능/시스템을 설계한다.

- **피드백 모드** — 기존 코드/폴더 구조를 분석해 VSA 원칙 위반 여부를 리뷰
- **설계 모드** — 새 기능의 슬라이스 구조, 패키지 역할, 슬라이스 간 통신 방법을 설계

**VSA 핵심 원칙:**
- `feature → core` 단방향 의존, 슬라이스 간 직접 참조 금지
- 슬라이스 간 데이터 전달은 원시 타입 또는 이벤트 기반

```
app/
  core/           — 앱 전반 공유 인프라
  features/
    {feature}/    — 기능별 수직 슬라이스
```

```bash
# 기존 구조 피드백
/architect

# 특정 폴더 피드백
/architect app/features/login/

# 새 기능 설계
/architect 결제 기능 추가
```

### `review-code`

코드 리뷰를 수행한다. Android / common 플랫폼을 자동 감지하고 가독성·정확성·보안·아키텍처·테스트 항목을 체크한다.

- 인자 없으면 `git diff HEAD` 기준으로 변경사항 전체 리뷰
- 인자 있으면 지정 파일/폴더 기준으로 리뷰
- Android 감지 시 Kotlin 컨벤션, Compose 패턴 기준 추가 적용

```bash
# 변경사항 전체 리뷰
/review-code

# 특정 파일/폴더 리뷰
/review-code app/features/login/
```

### `write-test`

대상 코드를 분석하고 테스트 시나리오를 함께 논의한 뒤 테스트 코드를 생성한다.

- 코드 분석 → 시나리오 논의 → 계획 승인 → 테스트 생성 순서로 진행
- Android 프로젝트 감지 시 BehaviorSpec, Fake/Mock 전략, StateFlow 검증 가이드라인 적용

```bash
/write-test app/features/login/LoginViewModel.kt
```

## 설치

```bash
/plugin install android@gagip-dev
```
