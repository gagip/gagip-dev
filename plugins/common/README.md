# common

언어/플랫폼 무관 공통 개발 도구 모음. 커밋, PR, 이슈, 코드 구현 등 개발 워크플로우 전반을 지원하는 스킬 모음.

## 스킬 목록

| 스킬 | 트리거 예시 |
| ---- | ----------- |
| `commit` | "커밋해줘", "변경사항 정리해줘", "커밋 메시지 만들어줘" |
| `changelog` | "체인지로그 써줘", "릴리즈 노트 만들어줘", "변경 이력 정리해줘" |
| `create-pr` | "PR 만들어줘", "풀리퀘 올려줘", "PR 본문 업데이트해줘" |
| `create-issue` | "이슈 만들어줘", "버그 등록해줘", "기능 요청 올려줘" |
| `apply-review` | "PR 리뷰 반영해줘", "리뷰 코멘트 처리해줘", "리뷰 적용해" |
| `implement` | "구현해줘", "만들어줘", "기능 추가해줘", "개발해줘" |

## 스킬 상세

### `commit`

변경사항을 분석하여 커밋 메시지를 작성하고 git 커밋을 수행한다.

- `git diff`와 `git status`로 변경사항을 파악하고 커밋 메시지 초안 제안
- Conventional Commits 형식 준수 (`feat:`, `fix:`, `chore:` 등)
- 사용자 확인 후 커밋 실행

```bash
/commit
```

### `changelog`

Git 커밋 이력을 분석하여 CHANGELOG 초안을 작성한다.

- 마지막 태그부터 HEAD까지 커밋 이력 분석
- `feat`, `fix`, `chore` 등 타입별로 분류하여 정리

```bash
/changelog
```

### `create-pr`

현재 브랜치의 변경사항을 분석하여 GitHub PR을 생성하거나 기존 PR 본문을 업데이트한다.

- 브랜치 커밋 이력을 분석하여 PR 제목·본문 초안 작성
- 사용자 확인 후 `gh pr create` 실행

```bash
/create-pr
```

### `create-issue`

GitHub 이슈를 생성한다. 버그 리포트, 기능 요청, 리팩토링, 문서 작업 등 모든 종류의 이슈를 지원한다.

```bash
/create-issue
```

### `apply-review`

GitHub PR 리뷰 코멘트를 가져와 우선순위 순으로 하나씩 검토하고, 사용자 승인 후 코드를 수정한다.

- 리뷰 코멘트를 Critical → Warning → Suggestion 순으로 처리
- 각 항목마다 사용자 승인 후 코드 수정

```bash
/apply-review
```

### `implement`

사용자와 함께 설계를 탐구한 뒤 구현 계획을 수립하고, 승인을 받아 코드를 구현한다.

- 설계 탐구 → 구현 계획 수립 → 승인 → 코드 구현 순서로 진행
- 구현 완료 후 작업 보고서 작성

```bash
/implement 로그인 기능 추가
```

## 에이전트

| 에이전트 | 트리거 예시 |
| -------- | ----------- |
| `skill-consistency-reviewer` | "스킬 일관성 확인해줘", "SKILL.md 리뷰해줘", "전체 스킬 일괄 점검해줘" |

## 훅

| 훅 | 동작 |
| -- | ---- |
| `block_sensitive_files` | `.env`, 시크릿 키 등 민감한 파일 수정 차단 |
| `validate_commit` | 커밋 메시지 컨벤션 검증 |

## 설치

```bash
/plugin install common@gagip-dev
```
