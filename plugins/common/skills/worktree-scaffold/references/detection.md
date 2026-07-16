# 레포 특이사항 감지 휴리스틱 (A / B / C / 관례)

`worktree-create.sh`를 채우기 전에 대상 레포에서 아래를 감지한다. 모두 **스택 무관 휴리스틱**이며, 확신이 안 서는 항목은
`AskUserQuestion`으로 사용자에게 확인한다.

## 목차
- [A. 복사 대상 — 추적 제외된 머신·환경 설정](#a-복사-대상)
- [B. 재생성 대상 — 체크아웃마다 다시 만들 산출물](#b-재생성-대상)
- [C. 격리 대상 — 동시 실행 시 충돌하는 자원](#c-격리-대상)
- [관례 감지 — base 브랜치·worktree 경로·러너](#관례-감지)
- [A와 B를 가르는 기준 (가장 흔한 실수)](#a와-b를-가르는-기준)

---

## A. 복사 대상

**정의**: gitignore돼 있어 새 worktree에 안 딸려오지만, **값이 그대로 유효**해 메인에서 복사하면 되는 머신·환경 설정 파일.

**감지 절차**:
1. `.gitignore` + `.git/info/exclude`에서 항목을 모은다.
2. 그중 *머신·환경 설정* 패턴(아래 표)에 해당하는 것만 후보로 남긴다.
3. 후보 중 **메인 체크아웃에 실제로 존재하는 파일만** 최종 복사 목록에 넣는다(없는 건 스킵). 하위 경로까지 확인한다 —
   설정이 모노레포 하위 패키지에 있을 수 있다(예: `packages/app/.env`).

**머신·환경 설정 패턴 (복사 대상)**:

| 분류 | 대표 패턴 |
|---|---|
| 환경 변수 | `.env`, `.env.*`, `*.env.local`, `.envrc` |
| 빌드 로컬 설정 | `local.properties`, `*.local.properties`, `gradle.local.properties` |
| 서명/키 | `*.keystore`, `*.jks`, `key.properties`, `*.p12`, `*.mobileprovision` |
| 서비스 자격증명 | `google-services.json`, `GoogleService-Info.plist`, `serviceAccount*.json`, `secrets*.{json,yaml}` |
| 에이전트/로컬 지침 | `CLAUDE.local.md`, `*.local.md`, `.claude/settings.local.json` |
| 로컬 작업 폴더 | `private/`(디렉터리째 복사) 같은 프로젝트 관례 폴더 |

> 주의: 이 표는 시작점이지 완결 목록이 아니다. 레포의 `.gitignore`를 실제로 읽어, "사람이 손으로 채우는 설정"으로 보이면
> 후보에 넣고, 애매하면 사용자에게 "이것도 복사할까요?"로 확인한다.

**복사 헬퍼**: 스크립트에서는 존재하지 않아도 하드 실패하지 않도록 `copy_if_exists`로 감싼다(골격 참조). 팀원마다 없는 설정이
있을 수 있기 때문이다.

---

## B. 재생성 대상

**정의**: gitignore돼 있지만 복사하면 깨지는(버전·경로·플랫폼 종속) 산출물. **명령을 재실행**해 만든다.

**감지 대상별**:

| 대상 | 감지 신호 | 재생성 명령 |
|---|---|---|
| 의존성(JS) | lockfile 존재 | `package-lock.json`→`npm ci`, `pnpm-lock.yaml`→`pnpm i --frozen-lockfile`, `yarn.lock`→`yarn install --immutable` |
| 의존성(기타) | `Cargo.lock`·`go.sum`·`Gemfile.lock` 등 | 해당 매니저 설치 명령(대개 빌드가 알아서 함 — 필요할 때만) |
| 빌드 프리스텝 | `package.json` scripts의 `prepare`/`postinstall`, 또는 README가 "먼저 X를 빌드"라고 지시(예: 로컬 패키지·i18n 번들) | 그 스크립트 실행(예: `npm run build:i18n`). 불명확하면 사용자 확인 |
| 네이티브 생성물 | Tauri(`src-tauri/tauri.conf.json`)·Capacitor·Expo prebuild 등, `gen/`·`android/`·`ios/`가 gitignore됨 | 예: `npx tauri <android\|ios> init`. 스택별로 다르니 신호를 보고 결정 |
| git hooks | `scripts/*hook*.sh`·`install-hooks.sh`·`.husky/`·`core.hooksPath` | 있으면 그 설치 스크립트 실행(worktree는 hooks가 공유 `.git`이라 재설치가 필요할 수 있음) |

> gradle 같은 순수 빌드 레포는 대개 B에서 재생성할 게 없다(`build/`는 빌드가 알아서 만든다). 그때는 B 섹션을 비우거나
> hooks 설치만 남긴다.

---

## C. 격리 대상

**정의**: 여러 worktree를 **동시에** 구동할 때 서로 밟는 자원. worktree마다 유일 값을 할당해 충돌을 막는다.

**감지**:
- **dev 서버가 있는가** — `package.json`에 `dev` 스크립트가 Vite/Next/webpack-dev-server 등을 띄우는가? 모바일 dev
  래퍼(예: `tauri <plat> dev`)가 로컬 서버·HMR 포트를 여는가?
- **동시 구동이 실제로 필요한가** — 여러 에이전트/브랜치를 병렬로 돌리는 워크플로면 격리가 의미 있다. 아니면 생략.

**격리 방법(dev 서버가 있을 때)**:
- 빈 포트 쌍을 스캔해(카운터가 아니라 "이미 점유된 포트 집합 + `lsof` 리스닝"을 둘 다 비운 값 채택 → 삭제된 worktree 포트
  자동 회수) worktree 로컬 env 파일(예: `.env.worktree`)에 고정 기록한다.
- 전용 `TMPDIR`을 worktree별로 만들어, 소켓/주소 파일(예: dev 서버가 `${TMPDIR}`에 쓰는 server-addr) 충돌을 막는다.
- dev 래퍼가 이 env를 `source`해 export하도록 안내한다.

**격리를 넣지 않는 경우(중요)**:
- **순수 빌드 레포(gradle 등)**: 빌드는 서버를 안 띄우므로 포트 격리가 무의미하다. 넣지 않는다.
- 저사양 머신에서 **직렬 빌드가 강제되는** 레포(문서에 "동시 빌드 금지" 류 제약이 있으면): 격리 대신 스크립트에 **직렬 실행을
  권고하는 주석**을 남긴다(동시 구동을 부추기지 않는다).

---

## 관례 감지

- **base 브랜치**: `git symbolic-ref refs/remotes/origin/HEAD`로 기본 브랜치를 얻거나, `develop`가 있으면 그 관례를 따른다.
  불명확하면 사용자에게 "base를 main으로 할까요, develop으로 할까요?" 확인. 스크립트는 `--base`로 오버라이드 가능하게 둔다.
- **worktree 경로 (자동 결정 금지 — 사용자에게 맡긴다)**: 경로는 스킬이 임의로 기본을 굳히지 말고 `AskUserQuestion`으로
  사용자가 고르게 한다. 두 선택지와 트레이드오프를 제시한다:
  - **레포 밖 (형제 `../<repo>-worktrees/<slug>`)**: `find`·`ripgrep`·IDE 인덱서 같은 비-git 도구가 worktree 사본까지 중복
    스캔하는 걸 피한다. 대신 정리는 수동(`git worktree remove`).
  - **레포 안 (`.claude/worktrees/<slug>` 등)**: 하네스/도구가 경로를 자동 관리하기 좋다. 대신 비-git 도구가 중복 스캔한다.

  사용자가 고른 값을 생성 스크립트의 **기본 경로**로 채우고, `--path` 오버라이드는 항상 남긴다. 레포에 이미 굳은 관례가
  보이면(예: 기존 worktree들이 한 위치에 몰려 있음) 그걸 기본 후보로 함께 제시한다.
- **러너 별칭**: `package.json`이 있으면 `"wt:new": "bash scripts/worktree-create.sh"` scripts 항목을 추가 제안. Makefile
  관례면 타깃. 둘 다 없으면 스크립트 직접 실행만 안내.

---

## A와 B를 가르는 기준

가장 흔한 실수는 gitignore된 걸 전부 "복사"로 처리하는 것이다. 판별 기준:

| 질문 | A(복사) | B(재생성) |
|---|---|---|
| 사람이 손으로 채운 설정인가? | 예 | 아니오 |
| 다른 머신에 복사해도 유효한가? | 예 | 아니오(버전·경로·플랫폼 종속) |
| 예 | `.env`, `local.properties`, keystore | `node_modules`, `build/`, `dist/`, `.gradle/`, `gen/` |

애매하면: "이 파일을 다른 컴퓨터에 그대로 복사해도 되나?"를 물어라. 되면 A, 다시 만들어야 하면 B다.
