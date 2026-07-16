---
name: worktree-scaffold
description: >
  레포의 환경·특이사항을 분석해 그 레포 전용 git worktree 부트스트랩 스크립트(`scripts/worktree-create.sh`)를
  일관된 골격으로 생성하는 스킬. `git worktree add`가 자동으로 안 딸려오는 것 — 추적 제외된 머신·환경 설정
  (`.env`·`local.properties`·keystore 등), 체크아웃마다 새로 만들어야 하는 산출물(node_modules·네이티브 생성물·git hooks),
  동시 실행 시 충돌하는 자원(dev 서버 포트·임시 디렉터리) — 을 자동 감지해, 복사(A)·재생성(B)·격리(C) 3단계와
  실패 롤백을 갖춘 스크립트를 만든다. 스킬 자신이 매번 세팅하는 게 아니라, 레포에 남아 재사용되는 스크립트를 짜주는 생성기다.
  다음 표현이 나오면 반드시 이 스킬을 사용한다: "worktree 셋업 스크립트 만들어줘", "worktree 생성 스크립트 짜줘",
  "worktree bootstrap 스크립트", "새 worktree에서 바로 개발되게 해줘", "worktree 만들면 .env/설정 자동 복사되게",
  "병렬 작업용 worktree 스크립트", "worktree-create.sh 만들어줘". worktree를 새로 만들면 빌드가 깨지거나 설정 파일이
  없어 매번 손으로 채운다고 호소할 때도, 사용자가 명시적으로 "스크립트"라 부르지 않아도 이 스킬로 해결한다.
allowed-tools: Bash, Glob, Grep, Read, Write, Edit, AskUserQuestion
argument-hint: (선택) 대상 레포 경로. 생략 시 현재 작업 디렉터리
---

# worktree-scaffold 스킬

대상 레포를 분석해 그 레포 전용 **`scripts/worktree-create.sh`** 한 개를 생성한다. 이후 사용자는 새 worktree가 필요할 때마다
이 스크립트를 실행하면 "즉시 개발 가능한" 상태의 worktree를 얻는다.

## 이 스킬이 푸는 문제 — `git worktree add`의 빈틈

`git worktree add`는 **git이 추적하는 파일만** 새 작업 트리에 실체화한다. 그래서 다음 세 부류는 새 worktree에 빠져 있고,
개발자가 매번 손으로 메꾸다 잊어 "worktree 만들었는데 빌드가 안 돼"가 반복된다:

- **A. 추적 제외된 머신·환경 설정** — `.env`, `local.properties`, 서명 keystore 같은 파일. gitignore돼 있어 안 딸려오지만
  값은 그대로 유효하므로 **복사**하면 된다.
- **B. 체크아웃마다 새로 만들어야 하는 산출물** — `node_modules`, 네이티브 코드 생성물, 설치형 git hooks. 복사가 아니라
  명령을 **재실행**해 만든다(버전·경로 종속이라 복사하면 깨진다).
- **C. 동시 실행 시 충돌하는 자원** — dev 서버 포트, 임시 디렉터리. worktree마다 **달라야** 하므로 빈 값을 새로 할당한다.

이 스킬의 정신모델은 이 **A(복사)·B(재생성)·C(격리) 3분류**다. 생성하는 스크립트는 항상 이 세 축으로 구조화된다.

## 정체성 — "세팅기"가 아니라 "스크립트 생성기"

worktree를 그 자리에서 직접 세팅해주는 런타임 도우미가 아니다. 이 스킬의 **산출물은 레포에 커밋되어 남는 스크립트**이고,
반복 실행은 사람(또는 CI)이 그 스크립트로 한다. 그래서:

- 스킬은 **한 번** 돌아 레포를 분석하고 스크립트를 쓴다. 이후 워크플로에서 스킬은 빠지고 스크립트만 남는다.
- 팀원·다른 세션이 같은 스크립트를 공유해 **결정적·재현적**으로 worktree를 만든다. AI가 매번 개입해 재감지하지 않는다.
- 레포마다 특이사항이 다르므로 스크립트 내용은 다르지만, **골격(섹션 구조)은 모든 레포에서 동일**하게 유지한다 — 이게
  "일관된 형식"의 실체다.

## 워크플로우

### 1단계 — 레포 분석 (특이사항 감지)

대상 레포 루트에서 A·B·C 후보와 관례를 감지한다. **상세 휴리스틱은 [references/detection.md](references/detection.md)를 읽고 따른다.**
핵심만:

- **A 후보**: `.gitignore`(+`.git/info/exclude`)에서 *머신·환경 설정* 패턴을 추리고, 그중 **메인 체크아웃에 실제로 존재하는
  파일만** 복사 목록에 넣는다. gitignore됐지만 재생성 대상(`node_modules`·`build/`·`dist/`·`.gradle/`)은 A가 아니라 B다 —
  둘을 반드시 구분한다.
- **B 후보**: 패키지 매니저(lockfile로 감지)·빌드 프리스텝·네이티브 생성물(예: Tauri `src-tauri`)을 찾아 재실행 명령을 정한다.
  git hooks는 worktree가 공용 `.git/hooks`를 상속하므로 **기본으로 재설치하지 않는다**(무리하게 `.git/hooks/`에 쓰면 오히려
  깨진다 — [references/detection.md](references/detection.md) 참고).
- **C 후보**: dev 서버(예: Vite/Next `dev` 스크립트)가 있고 병렬 구동이 의미 있으면 포트+TMPDIR 격리를 넣는다. 순수 빌드
  레포(예: gradle)면 격리를 넣지 않고, 자원 제약(저사양 직렬 빌드 등)이 문서에 있으면 직렬 실행 주석만 남긴다.
- **관례**: base 브랜치(main/develop), 러너 별칭(package.json script / Makefile).
- **worktree 경로는 자동으로 정하지 말고 사용자에게 확인한다** — 레포 안(`.claude/worktrees/`, 하네스 자동관리) vs 레포 밖
  (형제 디렉터리, `find`·`ripgrep`·IDE의 중복 스캔 회피)은 워크플로에 따라 답이 갈리는 트레이드오프다. `AskUserQuestion`으로
  둘의 장단을 제시해 고르게 하고, 그 선택을 생성 스크립트의 기본 경로로 채운다(`--path` 오버라이드는 항상 유지).

감지가 모호하거나 갈리면(예: base 브랜치가 불분명, 어떤 프리스텝을 넣을지) **`AskUserQuestion`으로 사용자에게 확인**한다.
추측으로 스크립트를 굳히지 않는다 — 잘못 넣은 단계는 나중에 스크립트를 통째로 고치는 재작업이 된다.

### 2단계 — 스크립트 생성 (일관 골격)

**[references/script-skeleton.sh](references/script-skeleton.sh)의 골격을 그대로 따르고**, 1단계에서 감지한 값으로 A·B·C 섹션을
채운다. 골격 순서는 어떤 레포든 동일하다:

```
usage/도움말 → 인자 파싱 → 경로 계산 → 사전검증 → 실패 롤백 트랩
 → 1.fetch base → 2.git worktree add
 → 3.[A] 추적제외 설정 복사 → 4.[B] 산출물 재생성 → 5.[C] 동시실행 자원 격리
 → 6.검증(선택) → 완료 안내
```

- **실패 롤백 트랩은 필수**다(`trap ... ERR`): 중간에 실패하면 worktree를 제거하되 **브랜치는 보존**한다. 반쯤 만들어진
  좀비 worktree를 남기지 않는다.
- 레포에 러너 관례가 있으면 별칭도 추가한다 — package.json이면 `"wt:new": "bash scripts/worktree-create.sh"`, Makefile이면
  타깃. 없으면 스크립트만 둔다.
- 존재하지 않는 A 파일은 `copy_if_exists`로 "경고 후 스킵"한다(하드 실패 금지) — 팀원마다 없는 설정이 있을 수 있다.

### 3단계 — 검증 (선택, 권장)

생성 직후 스크립트가 실제로 도는지 1회 실행해본다: 임시 브랜치로 worktree를 만들어 A·B·C가 통과하는지, (가능하면) 대상
레포의 대표 빌드/헬스체크까지 확인한다. 성공하면 그 임시 worktree는 정리한다. **직렬 빌드 제약이 있는 레포에서는 검증 실행이
다른 빌드와 겹치지 않게 한다.**

### 4단계 — 제시 & 커밋 안내

생성한 스크립트 경로와 사용법(`bash scripts/worktree-create.sh <branch>` 또는 러너 별칭)을 알려준다. **커밋·push는 스킬이
임의로 하지 않는다** — 대상 레포의 커밋 관례에 따라 사용자가 리뷰 후 커밋하도록 안내한다.

## 범용성 원칙

이 스킬은 임의의 레포에서 돈다. 특정 스택을 가정하지 말고 **감지 결과에 따라** A·B·C를 채운다. 감지로 못 좁히는 부분은
넓게 스캐폴딩하지 말고 `AskUserQuestion`으로 물어 좁힌다(가장 좁은 동작 범위로 시작). 스택별 감지 세부는
[references/detection.md](references/detection.md)에 스택 무관 휴리스틱으로 정리돼 있다.
