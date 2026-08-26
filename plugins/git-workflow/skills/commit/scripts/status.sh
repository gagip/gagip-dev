#!/usr/bin/env bash
# 커밋 전 변경사항 요약 출력
# 사용법: bash .claude/skills/commit/scripts/status.sh

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

echo "=== 변경 파일 ==="
git status --short

echo ""
echo "=== 스테이징된 변경사항 ==="
git diff --cached --stat

echo ""
echo "=== 스테이징되지 않은 변경사항 ==="
git diff --stat

echo ""
echo "=== 최근 커밋 5개 ==="
git log --oneline -5
