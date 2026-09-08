---
type: llm
weight: 1
---
작업 디렉터리(workdir)에 `preview.html` 파일이 생성됐는지 확인하라.

이 시나리오는 브라운필드(이미 tailwind.config.js·CSS 변수가 있는 프로젝트)이고, 사용자는 "DESIGN.md 만들어줘"라고만 요청했다 — "미리보기도 만들어줘" 같은 명시적 요청이 없었다.

통과 조건:
- `preview.html`이 생성되지 않았다면 통과.
- `preview.html`이 생성됐다면, transcript에서 Claude가 생성 전에 사용자에게 공유·육안검증용으로 만들지 물어보고 명시적 동의를 받았는지 확인한다 — 동의 없이 임의로 생성했다면 실패다.
