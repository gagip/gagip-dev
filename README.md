# gagip-dev

Claude Code와 Codex에서 함께 쓰는 개인 개발 워크플로 플러그인 마켓플레이스다. 하나의
`plugins/<plugin>/skills/` 트리를 두 하네스가 공유하며, 하네스 전용 도구가 없는 경우에는 같은
목적의 대화·파일·순차 실행 폴백을 사용한다.

## 플러그인

| 플러그인 | 설명 | 상세 |
|---|---|---|
| `common` | 계획·리뷰·회고 등 프로젝트 운영 스킬 | [plugins/common/README.md](plugins/common/README.md) |
| `development` | 커밋·PR·이슈 등 git/GitHub 작업 흐름과 코드 품질·모듈 구조 리뷰 스킬 | [plugins/development/README.md](plugins/development/README.md) |
| `design` | 디자인 시스템 결정을 문서화하는 스킬 | [plugins/design/README.md](plugins/design/README.md) |

## 설치

### Claude Code

```text
/plugin marketplace add gagip/gagip-dev
/plugin install common@gagip-dev
/plugin install development@gagip-dev
/plugin install design@gagip-dev
```

### Codex CLI

```bash
codex plugin marketplace add gagip/gagip-dev
codex plugin add common@gagip-dev
codex plugin add development@gagip-dev
codex plugin add design@gagip-dev
```

Codex는 저장소의 marketplace를 현재 작업 디렉터리만으로 자동 등록하지 않으므로 최초 한 번
`marketplace add`가 필요하다. 업데이트 후에는 `codex plugin marketplace upgrade gagip-dev`로
원격 snapshot을 갱신한 뒤 필요한 플러그인을 다시 설치한다.

## 호환성

- 배포 스킬 10개 중 9개는 Claude Code와 Codex에서 사용할 수 있다.
- `common:skill-metrics`는 Claude Code 로그가 기록하는 `Skill` 도구 호출을 지표로 쓰므로
  Codex에서는 지원하지 않는다. 스킬이 이를 감지해 이유를 알리고 종료한다.
- `allowed-tools`, `argument-hint`, `model` 같은 Claude Code frontmatter는 그대로 유지한다.
  Codex는 모르는 필드를 무시하고 `name`·`description`을 사용한다.

## 개발 및 검증

매니페스트·marketplace·플러그인 README의 중복 정보는 아래 검사로 맞춘다.

```bash
python3 scripts/check_consistency.py
```

Claude Code에서는 커밋 직전 훅이 이 검사를 자동 실행한다. 다른 하네스에서는 커밋 전에 수동으로
실행한다. Codex 매니페스트 스키마 검증은 내장 `plugin-creator`의 `validate_plugin.py`를 사용한다.

## 요구사항

- `gh` CLI: GitHub 이슈·PR 관련 스킬
- Python 3: 보고서 생성과 검증 스크립트
