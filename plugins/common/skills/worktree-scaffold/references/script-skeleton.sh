#!/usr/bin/env bash
# =============================================================================
# worktree-scaffold 골격 템플릿
#
# 이 파일은 생성될 `scripts/worktree-create.sh`의 "고정 골격"이다. worktree-scaffold
# 스킬은 이 순서·구조를 그대로 두고, `# ▼ [스킬이 채움] ▼` 로 표시된 A/B/C 섹션만
# 대상 레포의 감지 결과로 채운다. 고정 부분(인자 파싱·사전검증·롤백 트랩·완료 안내)은
# 어떤 레포에서든 동일하게 유지해 "일관된 형식"을 보장한다.
#
# 아래 값은 세탁된 예시(myproject)다. 실제 생성 시 레포에 맞게 치환한다.
# =============================================================================
set -euo pipefail

# ── 도움말 ───────────────────────────────────────────────────────────────────
usage() {
  cat <<EOF
사용법: $0 <branch-name> [옵션]

  <branch-name>    생성할 브랜치명 (예: feat/ABC-123-x)

옵션:
  --base <branch>   베이스 브랜치 (기본값: __BASE_BRANCH__)   # ▼ [스킬이 채움: 감지된 base] ▼
  --path <dir>      worktree 생성 경로 (기본값: __DEFAULT_WORKTREE_PATH_DESC__)   # ▼ [스킬이 채움: 사용자가 고른 위치] ▼
  --no-fetch        git fetch 스킵
  --no-install      의존성 설치/재생성 스킵
  -h, --help        도움말 출력
EOF
}

# ── 인자 파싱 ─────────────────────────────────────────────────────────────────
BRANCH=""
BASE="__BASE_BRANCH__"      # ▼ [스킬이 채움: main | develop 등] ▼
CUSTOM_PATH=""
NO_FETCH=0
NO_INSTALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --base)    BASE="$2"; shift 2 ;;
    --path)    CUSTOM_PATH="$2"; shift 2 ;;
    --no-fetch)   NO_FETCH=1; shift ;;
    --no-install) NO_INSTALL=1; shift ;;
    -*) echo "알 수 없는 옵션: $1" >&2; usage; exit 1 ;;
    *)
      if [[ -z "$BRANCH" ]]; then BRANCH="$1"
      else echo "인자가 너무 많습니다." >&2; usage; exit 1
      fi
      shift ;;
  esac
done

if [[ -z "$BRANCH" ]]; then
  echo "오류: branch-name이 필요합니다." >&2
  usage; exit 1
fi

# ── 경로 계산 ─────────────────────────────────────────────────────────────────
REPO_ROOT="$(git rev-parse --show-toplevel)"
REPO_NAME="$(basename "$REPO_ROOT")"
SLUG="${BRANCH//\//-}"

if [[ -n "$CUSTOM_PATH" ]]; then
  WORKTREE_PATH="$CUSTOM_PATH"
else
  # ▼▼▼ [스킬이 채움: 생성 시 사용자가 고른 기본 경로. 스킬이 임의로 정하지 않는다] ▼▼▼
  #   레포 밖(형제)   : "$(dirname "$REPO_ROOT")/${REPO_NAME}-worktrees/$SLUG"
  #   레포 안(하네스) : "$REPO_ROOT/.claude/worktrees/$SLUG"
  WORKTREE_PATH="__DEFAULT_WORKTREE_PATH__"
  # ▲▲▲ [여기까지 경로] ▲▲▲
fi

# ── 사전 검증 ─────────────────────────────────────────────────────────────────
if git worktree list --porcelain | grep -q "^worktree $WORKTREE_PATH$"; then
  echo "오류: '$WORKTREE_PATH' 는 이미 등록된 worktree 경로입니다." >&2
  exit 1
fi
if git worktree list --porcelain | grep -q "^branch refs/heads/$BRANCH$"; then
  echo "오류: '$BRANCH' 브랜치가 다른 worktree에 이미 체크아웃되어 있습니다." >&2
  git worktree list; exit 1
fi
if [[ -e "$WORKTREE_PATH" && -n "$(ls -A "$WORKTREE_PATH" 2>/dev/null)" ]]; then
  echo "오류: '$WORKTREE_PATH' 가 비어있지 않습니다." >&2
  exit 1
fi

# ── 실패 시 롤백 (EXIT 트랩 + 성공 플래그, 필수) ──────────────────────────────
# ERR 트랩은 서브셸 ( ... ) 안에서 난 실패에는 발화하지 않으므로 쓰지 않는다.
# EXIT 트랩에서 성공 플래그로 판정한다 — 끝까지 도달하지 못한 채(SUCCESS=0) worktree가
# 만들어졌으면 제거하되 브랜치는 보존한다(반쯤 만들어진 좀비 worktree 방지).
SUCCESS=0
WORKTREE_CREATED=0
cleanup() {
  if [[ $SUCCESS -eq 0 && $WORKTREE_CREATED -eq 1 ]]; then
    echo ""
    echo "⚠  실패 — worktree를 제거합니다 (브랜치는 보존)..."
    git worktree remove --force "$WORKTREE_PATH" 2>/dev/null || true
    git worktree prune 2>/dev/null || true
    echo "   원인 수정 후 다시 시도하세요: bash $0 $BRANCH --base $BASE"
  fi
}
trap cleanup EXIT

# ── 1. fetch base ─────────────────────────────────────────────────────────────
if [[ $NO_FETCH -eq 0 ]]; then
  echo "▶ fetching origin/$BASE ..."
  git fetch origin "$BASE"
fi

# ── 2. worktree 생성 ──────────────────────────────────────────────────────────
mkdir -p "$(dirname "$WORKTREE_PATH")"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "▶ 기존 브랜치 '$BRANCH' 로 worktree 생성 ..."
  git worktree add "$WORKTREE_PATH" "$BRANCH"
else
  echo "▶ 새 브랜치 '$BRANCH' (base: origin/$BASE) 로 worktree 생성 ..."
  git worktree add -b "$BRANCH" "$WORKTREE_PATH" "origin/$BASE"
fi
WORKTREE_CREATED=1

# ── 3. [A] 추적 제외된 머신·환경 설정 복사 ────────────────────────────────────
# git worktree add가 안 딸려온 gitignore 설정을 메인에서 복사한다. 값이 그대로 유효한 것만.
echo "▶ [A] 로컬 설정 복사 중 ..."
copy_if_exists() {
  local rel="$1" src="$REPO_ROOT/$1" dst="$WORKTREE_PATH/$1"
  if [[ -f "$src" ]]; then
    mkdir -p "$(dirname "$dst")"; cp "$src" "$dst"; echo "   복사: $rel"
  else
    echo "   경고: $rel 없음 (스킵)"
  fi
}
# ▼▼▼ [스킬이 채움: 감지된 A 파일 목록] ▼▼▼
copy_if_exists ".env"
copy_if_exists "local.properties"
copy_if_exists "CLAUDE.local.md"
# 디렉터리 통째 복사가 필요하면:
# [[ -d "$REPO_ROOT/private" ]] && cp -r "$REPO_ROOT/private" "$WORKTREE_PATH/private" && echo "   복사: private/"
# ▲▲▲ [여기까지 A] ▲▲▲

# ── 4. [B] 체크아웃마다 재생성할 산출물 ───────────────────────────────────────
# 복사하면 깨지는 것(버전·경로·플랫폼 종속)은 명령을 재실행해 만든다.
if [[ $NO_INSTALL -eq 0 ]]; then
  echo "▶ [B] 산출물 재생성 중 ..."
  cd "$WORKTREE_PATH"
  # ▼▼▼ [스킬이 채움: 감지된 B 명령들] ▼▼▼
  # 예) 의존성:      [[ -f package-lock.json ]] && (npm ci || npm install)
  # 예) 빌드 프리스텝: npm run build:i18n
  # 예) 네이티브:     ( cd packages/app && npx tauri android init )
  # 예) git hooks:    bash "$REPO_ROOT/scripts/setup-hooks.sh"
  # (순수 빌드 레포는 대개 여기 비움 — build/ 는 빌드가 알아서 만든다)
  # ▲▲▲ [여기까지 B] ▲▲▲
  cd "$REPO_ROOT"
fi

# ── 5. [C] 동시 실행 자원 격리 (dev 서버가 있을 때만) ─────────────────────────
# ▼▼▼ [스킬이 채움 또는 통째 삭제] ▼▼▼
# dev 서버가 있고 병렬 구동이 필요하면 빈 포트+전용 TMPDIR을 worktree 로컬 env에 고정한다.
# 순수 빌드 레포(gradle 등)면 이 섹션을 통째로 지우고 아래 직렬-빌드 주석만 남긴다:
#   # NOTE: 이 레포는 저사양 직렬 빌드 제약이 있다 — 여러 worktree에서 동시에 빌드하지 말 것.
#
# (dev 서버 레포용 예시)
# echo "▶ [C] dev 서버 자원 격리 중 ..."
# USED=" "
# while IFS= read -r l; do case "$l" in "worktree "*)
#   f="${l#worktree }/.env.worktree"; [[ -f "$f" ]] && USED+="$(grep -E '^WT_DEV_PORT=' "$f" | sed 's/.*=//') "
# ;; esac; done < <(git worktree list --porcelain)
# taken(){ [[ "$USED" == *" $1 "* ]] || lsof -i ":$1" >/dev/null 2>&1; }
# PORT=""; for ((c=14200;c<=14298;c+=2)); do taken "$c" || taken "$((c+1))" || { PORT=$c; break; }; done
# [[ -z "$PORT" ]] && { echo "오류: 빈 dev 포트 없음" >&2; exit 1; }
# WT_TMP="${TMPDIR:-/tmp}"; WT_TMP="${WT_TMP%/}/${REPO_NAME}-wt-${SLUG}"; mkdir -p "$WT_TMP"
# printf 'WT_DEV_PORT=%s\nTMPDIR=%s\n' "$PORT" "$WT_TMP" > "$WORKTREE_PATH/.env.worktree"
# echo "   포트=$PORT TMPDIR=$WT_TMP"
# ▲▲▲ [여기까지 C] ▲▲▲

# ── 6. 검증 (선택) ────────────────────────────────────────────────────────────
# ▼ [스킬이 채움: 대표 빌드/헬스체크. 직렬 빌드 제약 레포는 다른 빌드와 겹치지 않게] ▼
# 예) ( cd "$WORKTREE_PATH" && ./gradlew :app:assembleDebug -q )

# ── 완료 ──────────────────────────────────────────────────────────────────────
echo ""
echo "✅ worktree 셋업 완료!"
echo "   경로: $WORKTREE_PATH"
echo "   브랜치: $BRANCH"
echo ""
echo "   새 터미널에서: cd $WORKTREE_PATH"
SUCCESS=1   # 여기까지 도달해야 EXIT 트랩이 롤백을 건너뛴다
