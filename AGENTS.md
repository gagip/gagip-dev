# AGENTS.md — gagip-dev

Claude Code와 Codex가 함께 쓰는 개인 플러그인 마켓플레이스 레포다. `common`·`mobile` 플러그인의
스킬을 관리한다. 배포 스킬은 `plugins/<plugin>/skills/<skill>/SKILL.md`에 있고, 두 하네스가 같은
스킬 트리를 읽는다. 하네스 간 표현 규칙은 `docs/harness-vocabulary.md`를 정본으로 삼는다.

설치된 플러그인은 marketplace cache에서 동작하므로 변경을 실제로 시험하려면 marketplace 갱신과
재설치 후 새 대화를 시작한다.

## 공개 레포 원칙 (회사 고유명사 금지)

이 레포는 **공개 GitHub 레포**다. 회사 제품명·조직명·내부 레포명·내부 경로 같은 회사 고유명사를
커밋 메시지·CHANGELOG·스킬 문서·코드 예시에 넣지 않는다.

- 회사 코드베이스로 검증해도 결과를 남길 때는 제품·레포·경로 이름을 일반 용어로 치환한다.
- 커밋 전 공개되면 안 되는 고유명사가 섞이지 않았는지 staged diff를 확인한다.
- 로컬 메모리·개인 노트에는 실제 이름을 써도 되지만 이 레포 산출물에는 쓰지 않는다.

## Git 워크플로우

- **PR, 작업 브랜치, worktree를 쓰지 않는다.** `main` 체크아웃에서 직접 작업한다.
- 커밋은 이 레포의 `plugin-commit` 스킬을 따른다. 변경 경로로 scope를 감지하고
  `type(scope): 한글 메시지` 컨벤션을 사용한다.
- 원격에 올릴 때는 `release` 스킬을 거친다. `git push`를 직접 호출하지 않는다.
- push 권한은 개인 GitHub 계정 `gagip`을 쓴다. 다른 계정이 활성화돼 있으면 전환하고 작업 후 복원한다.

## 매니페스트 정합성

플러그인별로 Claude와 Codex 매니페스트가 함께 존재한다.

- Claude Code: `plugins/<plugin>/.claude-plugin/plugin.json`
- Codex: `plugins/<plugin>/.codex-plugin/plugin.json`
- Claude marketplace: `.claude-plugin/marketplace.json`
- Codex marketplace: `.agents/plugins/marketplace.json`

두 plugin manifest의 `name`·`version`·`description`은 항상 같아야 한다. 커밋 전 아래 검사를 실행한다.

```bash
python3 scripts/check_consistency.py
```

Claude Code에서는 Bash 커밋 직전 훅이 검사를 강제한다. 다른 하네스에서는 훅이 실행된다고 가정하지
말고 수동으로 실행한다.

## 릴리스 (스킬·플러그인 수정 시)

- 수정한 플러그인의 Claude와 Codex `plugin.json` 버전을 **같이** 범프한다.
- `plugins/<plugin>/CHANGELOG.md` 최상단에 새 버전 항목을 추가한다. 루트 `CHANGELOG.md`는 과거
  기록으로 동결되어 있으므로 갱신하지 않는다.
- CHANGELOG bullet은 앞선 구현 커밋 short hash를 참조한다.
- 구현 커밋과 릴리스 커밋(두 매니페스트 버전 + 플러그인 CHANGELOG)을 분리한다.
- 릴리스 전 Codex plugin validator와 `python3 scripts/check_consistency.py`를 모두 실행한다.
- 태그는 `<plugin>/v<version>` 형식을 사용한다.
