# product-d3

Product D3(Direction · Discovery · Delivery) 순환으로 제품을 만든다. 새 프로젝트와 기존 프로젝트에 같은 문서 구조
(루트 `PRODUCT.md`, 기능마다 `docs/features/<기능>/PRD.md`)와 같은 작업 생명주기(Understand → Define → Execute →
Verify → Finalize)를 건다.

`common`을 먼저 설치한다. 아래 스킬은 `common`의 스킬로 일을 넘긴다.

## 스킬

| 스킬 | 설명 | 트리거 예시 |
|---|---|---|
| `setup-d3` | 프로젝트 현황을 읽고 `PRODUCT.md`·`docs/`·`AGENTS.md`의 D3 블록을 깐다. 기존 파일은 덮어쓰지 않고 `CLAUDE.md`는 만들지 않음 | "D3 적용해줘", "새 프로젝트 D3로 시작하자" |
| `set-direction` | `PRODUCT.md`를 쓰거나 고치고, 기능이 방향에 맞는지 진행·보류·방향 변경으로 판정하고, 기존 기능을 점검 | "이거 우리 방향에 맞아?", "PRODUCT.md 고쳐줘" |
| `discover-problem` | 아이디어를 사용자·상황·문제로 다시 쓰고 근거를 관찰과 가설로 나눠 PRD 초안을 쓴 뒤 보류·실험·구현을 판정 | "이 기능 넣을 만해?", "다음에 뭘 풀지 정하자" |
| `validate-hypothesis` | 가정 하나를 가장 싼 방법으로 확인. 판정선을 `EXPERIMENTS.md`에 먼저 적고 실험 코드는 `experiments/`에만 둠 | "이 가정 확인해보자", "실험 설계해줘" |
| `deliver-work` | 코드 변경을 유형(Feature·Enhancement·Bug Fix·Refactoring)으로 가르고 계획 승인(필요할 때) → 구현 → 테스트·리뷰·범위 검사 → PRD 갱신 → PR·머지 → 보고까지 진행 | "~고쳐줘", "이 PRD 구현해줘", "리팩터링해줘" |
| `review-change` | 변경을 맥락 없는 검토자에게 넘겨 결함·요청에 없는 변경·미확인으로 판정. 범위 검사 스크립트와 D3 점검 7항목 | "PR 전에 봐줘", "이 diff 리뷰해줘" |
| `observe-outcome` | 출시 뒤 관찰을 PRD 성과 조건과 대조해 표본 충분성을 가르고, 원인을 결함 → 해결책 → 문제 가설 → 방향 순으로 분류 | "출시했는데 어때?", "성과 낮은데 방향 바꿀까" |

## common에 넘기는 일

| 일 | `common` 스킬 |
|---|---|
| 요구가 흐린 작업의 착수 전 인터뷰 | `grill` |
| 화면 방향을 시안으로 비교 | `compare-mockups` |
| 원자료가 남는 시장 조사 | `market-research` |
| 스킬 자체의 반복 평가 | `build-skill` |
| 회고 | `retrospective` |

## 에이전트

| 에이전트 | 하는 일 |
|---|---|
| `plan-reviewer` | 계획서를 실행 전에 기획·코드·디자인 중 지정받은 관점에서 회의적으로 검토한다. `deliver-work`의 Define 단계에서 바꿀 파일이 10개를 넘거나 되돌리기 비싼 작업일 때 호출한다 |

## 스크립트

| 스크립트 | 하는 일 |
|---|---|
| `inspect_project.py` | 프로젝트가 새것인지, 기존 지침·방향 문서·검증 명령이 무엇인지 JSON으로 보고 |
| `d3_scaffold.py` | `init`·`feature`·`experiment`로 틀을 만듦. 기존 파일은 건너뜀 |
| `check_d3_docs.py` | `PRODUCT.md` 일곱 칸, PRD 필수 칸, `EXPERIMENTS.md` 항목 형식, 링크 경로 검사 |
| `scope_check.py` | 기준 ref 대비 범위 밖 파일, 테스트 삭제·skip·단언 감소, 새 의존성 탐지 |
| `check_refs.py` | 플러그인을 임시 위치에 복사해 문서 안 상대경로가 모두 풀리는지 검사 |

모두 문제 없음 0, 문제 있음 1, 입력 폴더 없음 2로 끝난다. `check_d3_docs.py`는 `PRODUCT.md`가 없으면 1이다.
