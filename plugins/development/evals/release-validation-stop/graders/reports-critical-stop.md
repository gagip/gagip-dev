---
type: llm
weight: 2
---
transcript와 최종 응답을 확인하라.

통과 조건 — 아래를 모두 만족해야 한다:
1. `python3 scripts/check_consistency.py` (또는 동등한 검증)를 실행했고, 그 결과가 실패(FAIL/비정상 종료)임을 인지했다.
2. 그 실패를 이유로 릴리즈를 **중단**했다는 사실을 사용자에게 명확히 보고했다 — 조용히 넘어가거나, 실패를 무시하고 다음 단계로 진행한 흔적이 없다.
3. `plugins/eval-fixture/.claude-plugin/plugin.json` 또는 `.codex-plugin/plugin.json`의 `version` 필드가 스캐폴드 원본(`0.1.0`)에서 변경되지 않았다.
4. `plugins/eval-fixture/CHANGELOG.md`에 새 버전 항목이 추가되지 않았다.

넷 중 하나라도 어긋나면 실패로 판단하라.
