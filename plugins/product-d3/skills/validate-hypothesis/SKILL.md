---
name: validate-hypothesis
description: >
  Product D3 Discovery의 확인 단계이자 작업 유형 Experiment를 맡는다. 가정 하나를 가장 싼 방법(프로토타입·
  사용성 관찰·기술 검토·시안)으로 확인하되, 실행 전에 판정선(무엇을 얼마나 보고 어떤 결과면 진행할지)을
  EXPERIMENTS.md에 먼저 적고, 폐기 가능한 실험 코드는 experiments/에 두고, 결과를 통과·실패·유보로 판정해
  PRD에 반영한다. "이 가정 확인해보자", "프로토타입으로 검증해줘", "실험 설계해줘", "기술적으로 되는지
  봐줘", "실험 결과 정리해줘"에 사용한다. 문제 고르기는 discover-problem, 제품 코드 구현은
  deliver-work가 맡는다.
---

# validate-hypothesis

가정 하나에 답을 낸다. 틀렸다는 증거도 결과다. 기준은 [verification-system.md](../../references/verification-system.md)의 성과 조건, 생명주기는 [work-lifecycle.md](../../references/work-lifecycle.md)의 Experiment 행, 경로는 [paths-and-templates.md](../../references/paths-and-templates.md)를 따른다.

## 1. 가설

PRD에서 확인할 가정을 찾는다(없으면 사용자 말에서). 「<누가> <무엇을 하면> <무엇이 달라진다>」 한 문장으로 쓴다. 가정이 둘 이상이면 결정을 가장 크게 바꾸는 하나만 고른다.

## 2. 방법

가장 싼 방법을 고른다: 있는 자료 분석 → 수동 흉내 → 시안 → 프로토타입 → 기술 검토 코드. 프로토타입의 완성도는 가설이 요구하는 만큼만 둔다. 연출·조작감·소리가 가설의 핵심이면 그것까지 만든다. 화면 방향이 갈리는 가설이면 시안 비교(`compare-mockups`)가 맡는다고 알리고, 그 결과를 이 기록의 결과로 받는다.

## 3. 판정선 먼저

```bash
python3 <이 플러그인>/scripts/d3_scaffold.py experiment <slug> --feature <feature> --root <프로젝트>
```

`EXPERIMENTS.md` 새 항목에 가설·방법·판정선·표본·기간을 **실행 전에** 적는다. 판정선은 「무엇을 몇 건 보고, 어떤 값이면 통과·실패인가」다. 기준값을 모르면 「기준값을 잰 뒤 정함」으로 두고, 그 측정을 첫 실행으로 한다. 판정선을 사용자에게 보이고 확인받은 뒤 실행한다.

## 4. 실행

- 실험 코드는 `experiments/<날짜>-<slug>/`에만 둔다. 제품 코드(`src/` 등)를 고치지 않는다.
- 탐색이라도 안전·개인정보 제약은 지킨다. 실제 사용자 데이터를 쓰면 범위를 먼저 확인받는다.

## 5. 판정

- 결과를 판정선과 대조해 **통과·실패·유보** 중 하나로 `EXPERIMENTS.md`에 적는다. 결과를 본 뒤 판정선을 바꾸지 않는다. 바꿔야 하면 새 항목으로 다시 설계하고 이유를 남긴다.
- 표본·기간이 부족하면 유보와 필요한 증거를 적는다.
- 판정에 따라 PRD의 Solution·Scope·Success Criteria·Rationale(남은 위험)을 고친다.

| 판정 | 다음 |
|---|---|
| 통과 | 구현은 `deliver-work`가 맡는다 |
| 실패 | 해결책 재탐색은 `discover-problem`, 또는 보류 |
| 유보 | 필요한 증거를 모을 방법을 제안 |

```bash
python3 <이 플러그인>/scripts/check_d3_docs.py --root <프로젝트>
```
