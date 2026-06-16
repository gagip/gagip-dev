# CLAUDE.md — gagip-dev

개인 Claude Code 플러그인 마켓플레이스 레포. `common`·`android` 플러그인의 스킬을 관리한다.
스킬은 `plugins/<plugin>/skills/<skill>/SKILL.md`에 있고, 활성 스킬은 마켓플레이스 캐시에서 동작하므로
변경을 실제로 쓰려면 `/plugin` 마켓플레이스 업데이트 + 재설치가 필요하다.

## Git 워크플로우

- **이 레포는 PR도, 작업 브랜치도 쓰지 않는다.** 별도 브랜치를 만들지 말고 `main`에서 직접 작업·커밋한다. (전역 브랜치 원칙보다 이 레포 규칙이 우선이다.)
- 커밋은 **`plugin-commit` 스킬**로 수행한다 — 변경 경로로 scope를 자동 감지하고(`plugins/common` → `common`) `type: 한글 메시지` 컨벤션(`feat`/`fix`/`test`/`refactor`/`chore`)에 맞춘다.
- 원격에 올릴 때(push)는 **`release` 스킬**을 거친다 — 스킬 검증 → 버전 범프 → CHANGELOG → 커밋 → 태그 → push를 한 흐름으로 진행한다. `git push`를 직접 호출하지 않는다. (아래 `## 릴리스` 규칙을 release 스킬이 따른다.)
- push 권한은 **개인 GitHub 계정 `gagip`**을 쓴다. gh 활성 계정이 다른 계정이면 `gh auth switch --user gagip`로 전환해 push하고, 끝나면 원래 계정으로 복원한다.

## 릴리스 (스킬·플러그인 수정 시)

- 수정한 플러그인의 `plugins/<plugin>/.claude-plugin/plugin.json` `version`을 범프한다.
- 루트 `CHANGELOG.md`에 `## [<plugin>/<version>] — <YYYY-MM-DD>` 항목을 추가한다. 변경 bullet은 **구현 커밋의 short 해시**를 `([`hash`])`로 참조한다.
- **구현 커밋과 릴리스 커밋(버전 범프 + CHANGELOG)을 분리**한다 — 릴리스 커밋이 자기 자신의 해시를 참조하는 자기 참조 모순을 피하기 위해, CHANGELOG는 항상 앞선 구현 커밋 해시를 가리킨다.
