---
schema_version: "1.0"
name: release-happy-path
description: >
  ⚠️ 수동 전용 — CI에 연결하지 않는다. 검증이 전부 통과하는 신규 플러그인에서
  "릴리즈해줘"를 요청했을 때, release 스킬이 실제로 버전 확정(신규 플러그인이라
  범프 없이 0.1.0 유지)·CHANGELOG 기록·커밋·태그·push까지 중단 없이 끝내는지
  검증한다. 대상은 gagip 소유의 개인 스크래치 저장소 gagip/eval-scratch —
  이 suite를 실행하면 그 저장소에 실제 커밋과 태그가 push된다.
  주기적으로 쌓인 eval 태그를 정리해야 할 수 있다.
tags: [release, happy-path, manual-only]
runs: 1
expected_outcome: >
  check_consistency.py 스텁이 통과하고, release 스킬이 신규 플러그인 규칙에
  따라 버전 범프 없이 0.1.0으로 CHANGELOG 항목을 추가하고, 커밋·태그
  (eval-fixture-happy/v0.1.0)·push를 중단 없이 끝낸 뒤 완료 보고를 낸다.
max_turns: 25
timeout_seconds: 400
allowed_tools: [Bash, Read, Write, Edit, Glob, Grep]
scaffold_script: |
  set -e
  git clone -q https://github.com/gagip/eval-scratch.git .
  git config user.email "eval@example.com"
  git config user.name "Eval Bot"
  mkdir -p plugins/eval-fixture-happy/.claude-plugin plugins/eval-fixture-happy/.codex-plugin plugins/eval-fixture-happy/skills/noop scripts
  cat > plugins/eval-fixture-happy/.claude-plugin/plugin.json <<'EOF'
  {
    "name": "eval-fixture-happy",
    "version": "0.1.0",
    "description": "Eval fixture - happy path"
  }
  EOF
  cat > plugins/eval-fixture-happy/.codex-plugin/plugin.json <<'EOF'
  {
    "name": "eval-fixture-happy",
    "version": "0.1.0",
    "description": "Eval fixture - happy path"
  }
  EOF
  cat > plugins/eval-fixture-happy/skills/noop/SKILL.md <<'EOF'
  ---
  name: noop
  description: eval 전용 더미 스킬. 아무 것도 하지 않는다.
  allowed-tools: Read
  ---
  아무 작업도 수행하지 않는다.
  EOF
  cat > plugins/eval-fixture-happy/CHANGELOG.md <<'EOF'
  # Changelog
  EOF
  cat > scripts/check_consistency.py <<'PYEOF'
  print("OK: eval 스텁 - 항상 통과")
  PYEOF
  git add -A
  git commit -q -m "feat(eval-fixture-happy): eval 전용 더미 플러그인 추가"
---
릴리즈해줘
