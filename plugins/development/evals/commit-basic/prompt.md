---
schema_version: "1.0"
name: commit-basic
description: >
  스테이징되지 않은 변경사항이 있는 저장소에서 "커밋해줘"라고 요청했을 때
  commit 스킬이 status.sh로 상태를 파악하고, git add -A로 전체 변경사항을
  스테이징한 뒤, commit-guidelines.md 형식의 커밋 메시지로 커밋하고,
  완료 메시지를 정해진 포맷으로 출력하며, push는 하지 않는지 검증한다.
tags: [commit, smoke]
runs: 3
expected_outcome: >
  git add -A 후 "<type>: <한글 요약>" 형식의 메시지로 커밋이 생성되고,
  "✅ 커밋 완료!" 포맷의 완료 메시지가 출력된다. git push는 호출되지 않는다.
max_turns: 15
timeout_seconds: 180
allowed_tools: [Bash, Read, Skill]
scaffold_script: |
  set -e
  git init -q
  git config user.email "eval@example.com"
  git config user.name "Eval Bot"
  printf 'console.log("hello");\n' > app.js
  git add app.js
  git commit -q -m "chore: 초기 스캐폴드 커밋"
  printf 'console.log("hello world");\n' > app.js
  printf '# Notes\n\nscratch notes for eval\n' > NOTES.md
---
커밋해줘
