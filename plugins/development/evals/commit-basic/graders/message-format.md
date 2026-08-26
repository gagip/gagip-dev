---
type: llm
weight: 1
---
transcript에서 실제로 실행된 `git commit -m "..."` (또는 heredoc으로 전달된) 커밋 메시지를 찾아라.

통과 조건:
- 메시지 첫 줄이 `<type>: <한글 요약>` 형식이다 (예: `chore: 스캐치 노트 추가`).
- `<type>`이 다음 중 하나다: feat, fix, refactor, style, test, docs, chore, ai.
- 요약이 실제 변경사항(app.js 수정, NOTES.md 추가)과 무관하지 않다 — 완전히 엉뚱한 내용이면 안 된다.

커밋 메시지를 찾지 못했거나 형식을 지키지 않았으면 실패로 판단하라.
