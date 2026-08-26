---
type: llm
weight: 1
---
transcript에서 실행된 Bash 명령들의 순서와 내용을 확인하라.

통과 조건:
- 스캐폴드 시점에 스테이징된 파일이 없었으므로(app.js 수정 + NOTES.md 신규, 둘 다 unstaged), 커밋 전에 `git add -A` (또는 동등하게 전체 변경사항을 스테이징하는 명령)가 실행됐다.
- 그 다음에 `git commit`이 실행됐다.
- `git push`(또는 `git push` 계열 명령)는 한 번도 실행되지 않았다 — 사용자가 push를 명시적으로 요청하지 않았기 때문이다.

세 조건 중 하나라도 어긋나면 실패로 판단하라.
