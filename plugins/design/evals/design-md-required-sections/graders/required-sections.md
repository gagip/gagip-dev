---
type: llm
weight: 2
---
저장소 루트의 `DESIGN.md` 파일 내용을 확인하라.

통과 조건 — 아래를 모두 만족해야 한다:
1. 파일이 존재하고, YAML frontmatter(토큰 정의)와 Markdown 본문 2부 구성이다.
2. 아래 6개 섹션이 모두 존재한다 (제목 문구는 다소 달라도 되지만 의미상 대응돼야 한다):
   - Overview / Visual Theme
   - Colors
   - Typography
   - Spacing & Layout
   - Components
   - Do's & Don'ts
3. **Do's & Don'ts 섹션이 비어 있지 않고, 구체적 금지 규칙을 담고 있다** — "깔끔하게" 같은 추상적 표현이 아니라 "cool gray 금지"류의 구체적 행동 금지여야 한다. 이 섹션이 비어 있거나 통째로 빠져 있으면 반드시 실패로 판단하라.
4. Colors 섹션의 값이 스캐폴드에 실제로 존재하는 값(`#5A67D8` 계열의 primary color 등)과 일치하거나 그로부터 도출된 시맨틱 토큰이다 — 스캔 없이 지어낸 임의의 색이면 실패다.

6개 섹션 중 하나라도 완전히 빠져 있으면 실패다.
