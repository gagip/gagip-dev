# CHANGELOG

## [0.1.3] - 2026-11-27

### 🐛 Fix
- **deliver-work**: 일회성 스크립트 작성("스크립트 짜줘")과 답변에 넣을 짧은 코드("함수 하나 짜줘")에도 열리도록 description 트리거를 보강하고 발동 케이스 둘을 더한다 (`392b350`)

## [0.1.2] - 2026-11-27

### 📝 Docs
- **coding-philosophy**: 릴리스 빌드에서 꺼지는 `assert`에 기대지 않는 규칙과, 경계를 프로세스를 넘는지로 가르는 기준(자사 서버 포함)을 넣는다 (`3924f79`)

## [0.1.1] - 2026-11-27

### 📝 Docs
- **README**: 공용 스킬 목록에서 `session-doc`을 뺀다 (`cdf0b2a`)

## [0.1.0] - 2026-11-26

### ✨ Feat
- **setup-d3**: 프로젝트 현황을 읽고 `PRODUCT.md`·`docs/`·`AGENTS.md`의 D3 블록을 깐다. 기존 파일은 덮어쓰지 않고 `CLAUDE.md`는 만들지 않는다 (`32d4299`)
- **set-direction**: `PRODUCT.md`를 쓰고 고치며, 기능이 방향에 맞는지 진행·보류·방향 변경으로 판정하고 기존 기능을 점검한다 (`20bdc60`)
- **discover-problem**: 아이디어를 사용자·상황·문제로 다시 쓰고 근거를 관찰과 가설로 나눠 PRD 초안을 쓴 뒤 다음 활동을 판정한다 (`2eb0344`)
- **validate-hypothesis**: 판정선을 `EXPERIMENTS.md`에 먼저 적고 실험 코드는 `experiments/`에만 둔다 (`02304a4`)
- **deliver-work**: common `dev`를 옮겨 D3 생명주기와 작업 유형 넷으로 다시 쓴다. git·PR·머지 규칙은 그대로다 (`71c191e`)
- **review-change**: 범위 검사와 D3 점검 7항목으로 변경을 독립 검토한다 (`b7914f3`)
- **observe-outcome**: 출시 뒤 관찰을 성과 조건과 대조하고 원인을 결함 → 해결책 → 문제 가설 → 방향 순으로 분류한다 (`f603583`)
- **scripts**: `inspect_project`·`d3_scaffold`·`check_d3_docs`·`scope_check`·`check_refs` (`28277bb`)

### 🐛 Fix
- **scripts**: `d3_scaffold`가 하위 명령 뒤 `--root`를 받고 틀린 날짜를 거부한다. `scope_check`가 한글 경로를 읽는다 (`4b8fce4`)
- **observe-outcome·set-direction·discover-problem**: 원인 분기에 문제 가설 재검토를 되살리고 세 스킬의 맡는 범위를 가른다 (`4b8fce4`)
