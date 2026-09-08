---
type: llm
weight: 2
---
`plugins/eval-fixture-happy/.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `CHANGELOG.md`를 확인하라.

통과 조건:
1. 신규 플러그인 첫 릴리스이므로 두 plugin.json의 `version`은 그대로 `0.1.0`이다(자동 범프 없음).
2. `CHANGELOG.md`에 `## [0.1.0] - YYYY-MM-DD` 형식의 새 항목이 최상단에 추가됐다.
3. 완료 보고에 "신규 플러그인 첫 릴리스 — 범프 없음"에 준하는 안내가 있다.
