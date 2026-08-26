---
schema_version: "1.0"
name: draft-plan-structure
description: >
  GitHub 이슈 없이 자연어 주제만으로 계획서를 요청했을 때, draft-plan 스킬이
  Plan Mode에 진입해 PRD 골격(배경/문제 정의, 목표/비목표, 요구사항,
  성공 지표/검증 방법, 리스크/오픈 이슈)을 갖춘 계획서를 작성하는지 검증한다.
  특히 SKILL.md가 "가장 자주 빠진다"고 스스로 명시한 비목표·리스크 절이
  실제로 채워지는지가 핵심이다.
tags: [draft-plan, structure]
runs: 3
expected_outcome: >
  EnterPlanMode로 진입해 탐색·논의 후, 5개 필수 절을 모두 갖춘 PRD 형식
  계획서를 작성한다. 요구사항은 결정|이유 표로 정리되고, 코드 전문이나
  파일별 작업 순서표는 포함되지 않는다.
max_turns: 40
timeout_seconds: 600
allowed_tools: [Bash, Read, Write, Glob, Grep, WebSearch, WebFetch, EnterPlanMode, ExitPlanMode, Skill]
scaffold_script: |
  set -e
  git init -q
  git config user.email "eval@example.com"
  git config user.name "Eval Bot"
  mkdir -p src
  cat > src/cli.py <<'PYEOF'
  import argparse

  def main():
      parser = argparse.ArgumentParser(description="Sample CLI tool")
      parser.add_argument("name")
      args = parser.parse_args()
      print(f"Hello, {args.name}!")

  if __name__ == "__main__":
      main()
  PYEOF
  git add -A
  git commit -q -m "chore: 초기 CLI 스캐폴드"
---
src/cli.py에 --verbose 플래그를 추가해서, verbose 모드일 때만 추가 디버그 로그를 찍게 하고 싶어. 계획서 세워줘.
