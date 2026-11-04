# AGENTS.md — gagip-dev

Claude Code와 Codex가 함께 쓰는 개인 플러그인 마켓플레이스 레포다. `common` 플러그인의
스킬을 관리한다. 배포 스킬은 `plugins/<plugin>/skills/<skill>/SKILL.md`에 있고, 두
하네스가 같은 스킬 트리를 읽는다. 하네스 간 표현 규칙은 `docs/harness-vocabulary.md`를 정본으로
삼는다.

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
- 저장소 관리 스킬(`plugin-commit`, `release`)은 `.claude/skills/`에만 두는 Claude Code 전용이다.
  이 레포는 Codex로 작업하지 않으므로 `.agents/skills/`와 심볼릭 링크를 두지 않는다. 배포
  플러그인(`plugins/`)의 Codex 지원은 그대로 유지한다.

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

## 스킬 등록 기준

스킬은 적을수록 좋다. 엄격하고 확실한 것만 올리며, 아래를 모두 충족해야 한다.

1. **역할과 트리거가 분명하다.** 개발 흐름의 단계가 아니어도 된다. 부르는 말과 쓸 상황을 한 줄로
   쓸 수 있어야 한다.
2. **다른 수단으로 대체되지 않는다.** CLI 한 줄, MCP 서버 자체 지침, 모델 기본 능력으로 되면 만들지 않는다.
3. **도메인 특화는 도메인 플러그인으로 분리한다.** `common`에는 도메인 무관 스킬만 둔다. 도메인
   플러그인도 나머지 기준은 똑같이 적용한다.
4. **기존 스킬과 겹치지 않는다.** 겹치면 합친다. description에 이웃 스킬과의 경계를 적는다.
5. **결정론적 테스트(eval)가 있다.**
6. **산출물 형식을 고정해 자유도를 잃지 않는다.** 템플릿이 결과물을 한 모양으로 굳히면 만들지 않는다.

### 퇴출

호출 횟수나 일수로 판단하지 않는다. 가끔 쓰는 스킬은 한 달 호출이 0이어도 정상이다. 아래 중 하나면
제거 후보로 올린다.

- 쓸 상황이 있었는데 불리지 않았다. 상황 자체가 없었다면 후보가 아니다.
- 대체 수단이 생겼다.
- eval이 깨진 채 방치된다.

사용 지표(`agent-env-diagnosis`)는 참고 자료로만 쓴다. 도메인 플러그인은 플러그인 단위로 판단한다.

## 릴리스 (스킬·플러그인 수정 시)

- 수정한 플러그인의 Claude와 Codex `plugin.json` 버전을 **같이** 범프한다.
- `plugins/<plugin>/CHANGELOG.md` 최상단에 새 버전 항목을 추가한다. 루트 `CHANGELOG.md`는 과거
  기록으로 동결되어 있으므로 갱신하지 않는다.
- CHANGELOG bullet은 앞선 구현 커밋 short hash를 참조한다.
- 구현 커밋과 릴리스 커밋(두 매니페스트 버전 + 플러그인 CHANGELOG)을 분리한다.
- 릴리스 전 `python3 scripts/release_check.py --plugin <plugin>`을 실행한다. 일관성·구조 검사, 전체 단위 테스트, 바뀐 스킬의 평가를 돌린다.
- 태그는 `<plugin>/v<version>` 형식을 사용한다.
