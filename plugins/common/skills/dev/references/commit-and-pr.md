# 커밋·PR 기본 형식

프로젝트·전역 지침이 커밋·PR 형식을 정하지 않았을 때 쓴다.

## 커밋 메시지

```text
<type>: <변경 내용 한 줄 요약>

<선택: 구현 방식·설계 결정 이유 또는 문제 원인과 수정 방법. 개조식>
```

| type | 사용 상황 |
|---|---|
| `feat` | 새 기능 추가 |
| `fix` | 버그·race condition 수정 |
| `refactor` | 기능 변경 없는 구조 개선 |
| `style` | 접근성·UI 변경 |
| `test` | 테스트 추가·수정 |
| `docs` | 문서 작성·수정 |
| `chore` | 빌드·설정 변경 |
| `ai` | AI 지침·가이드라인·프롬프트 문서 변경 |

- 커밋 전에 `git status --short`·`git diff --stat`·`git log --oneline -5`로 변경과 최근 메시지 형식을 본다.
- 스테이징된 파일이 있으면 그것만 커밋한다. 없으면 이번 작업에서 바꾼 파일만 골라 스테이징한다. 포함할 파일을 사용자에게 되묻지 않는다.

## PR

- 제목은 `<type>: <요약>`이다. 본문은 개조식으로 쓴다.
- base는 `git symbolic-ref refs/remotes/origin/HEAD`로 감지하고, 실패하면 `main`이다. 변경은 `git log <base>..HEAD --oneline`·`git diff <base>...HEAD --stat`로 모은다.
- 브랜치가 원격에 없으면 `git push -u origin HEAD` 후 `gh pr create`. 기본은 ready이고, 사용자가 요청할 때만 `--draft`. 리뷰어·라벨은 필요할 때 `--reviewer`·`--label`.
- 이미 PR이 있으면 `gh pr view --json body`로 기존 본문을 읽고 바뀐 부분만 고쳐 `gh pr edit`. draft/ready 상태는 바꾸지 않는다.
- 본문 칸: 요약(1~2문장) · 주요 변경 · 구현 방식 · 이 방식을 고른 이유와 검토한 대안 · 검증(돌린 명령과 결과, 못 한 것은 "미검증").
- 본문에 외부 협업자가 알 필요 없는 내부 정보를 넣지 않는다: 로컬 경로·내부 IP·개인 메모·로컬 계획서 내용·임시 분석과 디버깅 흔적.
