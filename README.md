# gagip-dev

Claude Code 플러그인 마켓플레이스. 개발 워크플로우 자동화 스킬 모음.

## 플러그인 목록

### `common` — 공통 개발 도구

언어·플랫폼 무관하게 사용할 수 있는 스킬.

| 스킬           | 트리거 예시                                     |
| -------------- | ----------------------------------------------- |
| `implement`    | "구현해줘", "기능 추가해줘", "만들어줘"         |
| `apply-review` | "PR 리뷰 반영해줘", "코드리뷰 코멘트 처리해줘" |
| `commit`       | "커밋해줘", "변경사항 정리해줘"                 |
| `create-pr`    | "PR 만들어줘", "풀리퀘 올려줘"                  |
| `create-issue` | "이슈 만들어줘", "버그 등록해줘"                |
| `write-report` | "보고서 써줘", "작업 정리해줘"                  |

### `android` — Android 개발 전용

Android 프로젝트에 특화된 스킬.

| 스킬          | 트리거 예시                                   |
| ------------- | --------------------------------------------- |
| `architect`   | "아키텍처 봐줘", "구조 리뷰해줘", "설계해줘" |
| `review-code` | "리뷰해줘", "코드 봐줘", "코드 점검"          |
| `write-test`  | "테스트 써줘", "단위 테스트 추가"             |

## 스킬 상세

### `implement`

설계를 함께 탐구한 뒤 구현 계획을 수립하고, 승인 후 코드를 구현한다. 소크라테스식 질문으로 사용자가 직접 설계를 이끌도록 유도한다.

### `apply-review`

GitHub PR 리뷰 코멘트를 가져와 우선순위 순으로 하나씩 검토하고, 승인 후 코드를 수정한다.

**요구사항**: Python, `gh` CLI 인증 완료

### `commit`

변경사항을 분석해 커밋 메시지 초안을 작성하고, 승인 후 커밋한다.

### `create-pr`

현재 브랜치의 변경사항을 분석해 PR 본문 초안을 작성하고, 승인 후 PR을 생성하거나 기존 PR을 업데이트한다.

### `create-issue`

버그 리포트, 기능 요청, 리팩토링 등 GitHub 이슈를 생성한다. 레포의 실제 라벨을 감지해 자동으로 적용한다.

### `write-report`

작업 완료 후 `dev/report/`에 작업 보고서를 작성한다. "무엇을 했는가"보다 "왜 이렇게 결정했는가"에 집중한다.

### `architect`

수직 슬라이스 아키텍처(VSA) 기반으로 프로젝트를 피드백하거나 새 기능/시스템을 설계한다. 기존 코드가 있으면 피드백 모드, 새 설계 요청이면 설계 모드로 자동 전환한다.

### `review-code`

코드 리뷰를 수행한다. 플랫폼(Android / common)을 자동 감지하고, 가독성·정확성·보안·아키텍처·테스트 항목을 체크한다.

```bash
# 변경사항 전체 리뷰
/review-code

# 특정 파일/폴더 리뷰
/review-code src/feature/login/
```

### `write-test`

대상 코드를 분석하고 테스트 시나리오를 논의한 뒤 테스트 코드를 생성한다.

```bash
/write-test src/feature/login/LoginViewModel.kt
```

## 설치

```bash
# 1. 마켓플레이스 추가
/plugin marketplace add gagip/gagip-dev

# 2. 플러그인 설치
/plugin install common@gagip-dev
/plugin install android@gagip-dev
```

## 요구사항

- `gh` CLI (GitHub 관련 스킬 사용 시)
- Python (`apply-review` 스킬 사용 시)
