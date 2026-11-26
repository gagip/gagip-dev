# 경로와 문서 틀

## 경로 정하기

1. 프로젝트 `AGENTS.md`(또는 그 프로젝트의 지침 파일)가 `PRODUCT.md`·PRD 위치를 정했으면 그 경로를 쓴다.
2. 없으면 루트 `PRODUCT.md`, `docs/features/<feature>/PRD.md`를 쓴다. `<feature>`는 영문 소문자·숫자·하이픈.
3. 위치를 찾지 못했는데 이미 다른 이름의 방향 문서가 있으면 새로 만들지 않고 그 문서를 쓸지 사용자에게 묻는다.

## 틀 만들기

틀은 스크립트로 만든다. 이미 있는 파일은 덮어쓰지 않는다.

```bash
python3 <플러그인>/scripts/d3_scaffold.py init --root <프로젝트> [--verify-command "<명령>"]
python3 <플러그인>/scripts/d3_scaffold.py feature <feature> --root <프로젝트>
python3 <플러그인>/scripts/d3_scaffold.py experiment <slug> --feature <feature> --root <프로젝트>
```

틀 원본: `assets/templates/`의 `PRODUCT.md`·`PRD.md`·`AGENTS-block.md`·`EXPERIMENTS-entry.md`·`experiment-README.md`.

## 검사

```bash
python3 <플러그인>/scripts/check_d3_docs.py --root <프로젝트>
```

`PRODUCT.md` 일곱 칸, PRD 필수 칸(Purpose·Problem·Scope·Success Criteria), 상대 링크, 실험 기록 형식을 본다. 오류가 있으면 고친다. 경고(PRD 체크리스트)는 완료 조건을 테스트로 옮겼는지 보고 판단한다.

## PRD 칸

| 칸 | 담는 것 | 언제 채우나 |
|---|---|---|
| Purpose | 기능이 왜 있나 | 탐색 시작 |
| Problem | 누구의 어떤 상황·문제, 관찰(출처·시점)과 가설 | 탐색 |
| Solution | 후보와 고른 안 | 탐색 끝 |
| Requirements | 사용자에게 보장할 것. 구현 전 합의할 상세 동작·완료 조건은 임시로 적고, 계약·테스트로 옮기면 지운다 | 구현 전 |
| Scope / Non-goals | 이번에 하는 것과 하지 않는 것 | 구현 전 |
| Constraints | 규제·외부 의존·기술 제약과 바꿀 수 있는지 | 필요할 때 |
| Success Criteria | 성과 조건: 대상·관찰 항목·판정 기준·볼 날 | 구현 전(신규 기능은 필수) |
| Rationale | 선택 이유, 버린 안, 남은 불확실성, 바뀐 이유(날짜) | 결정할 때마다 |
| References | 조사·디자인·결정 기록, 동작을 보장하는 코드·테스트 위치 | 구현 뒤 |

- 기능 규모에 맞게 필요한 칸만 채운다. 빈 칸은 틀 그대로 둬도 된다.
- 리팩터링이나 내부 구현 변경만으로는 PRD를 고치지 않는다. 사용자 경험·범위·요구사항이 바뀌면 고친다.

## 보조 문서와 폴더

| 파일·폴더 | 만드는 때 | 관리 |
|---|---|---|
| `docs/features/<f>/DESIGN.md` | 흐름·와이어프레임·상호작용 근거가 PRD 한 절을 넘을 때. 시안 경로와 고른 이유를 적는다 | UX 의도가 바뀔 때 고침 |
| `docs/features/<f>/RESEARCH.md` | 조사·관찰을 보존할 가치가 있을 때 | 출처·시점과 함께 추가 |
| `docs/features/<f>/EXPERIMENTS.md` | 실험을 할 때 | 항목 추가. 판정선은 실행 전에 |
| `docs/features/<f>/DECISIONS.md` | PRD Rationale로 부족할 때: 결정이 대체 관계를 갖게 되거나 길어질 때 | 새 결정 추가, 대체 여부 표시 |
| `docs/decisions/` | 기능 둘 이상에 걸리는 결정 | 위와 같음 |
| `docs/design/`·`docs/architecture/`·`docs/research/` | 제품 공통 지식이 실제로 생겼을 때 | |
| `experiments/<날짜>-<slug>/` | 실험 코드·프로토타입. 첫 줄에 「폐기 가능」 | 제품 코드와 섞지 않음 |
| `src/`·`tests/`·`assets/` | 프레임워크가 정한 위치를 따른다. 같은 책임의 폴더를 새로 만들지 않는다 | |

폴더는 필요가 생길 때 만든다. 단계별 폴더를 만들지 않는다.
