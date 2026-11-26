---
name: discover-problem
description: >
  Product D3 Discovery의 앞부분을 맡는다. 아이디어·피드백을 사용자·상황·문제로 다시 쓰고 PRODUCT.md에
  대입하고, 사용 기록·관찰에서 근거를 찾아 사실과 가설을 나누고, 해결책 후보를 비교해 결정을 바꿀
  가정 하나를 고른 뒤 기능 PRD 초안을 쓰고 보류·실험·구현 중 다음 활동을 판정한다. "이 아이디어 해볼까",
  "이 기능 넣을 만해?", "다음에 뭘 풀지 정하자", "사용자 문제 찾아줘", "새 기능 검토해줘"에 사용한다.
  방향에 맞는지만 묻는 요청과 방향 자체를 고치는 일은 set-direction, 가정을 실험으로 확인하는 일은
  validate-hypothesis, 구현은 deliver-work가 맡는다.
---

# discover-problem

기능 하나의 문제를 고르고 근거를 세운다. 결과는 PRD 초안과 다음 활동 판정이다. 기준은 [d3-core.md](../../references/d3-core.md), 경로와 PRD 칸은 [paths-and-templates.md](../../references/paths-and-templates.md), 사람이 정할 곳은 [work-contract.md](../../references/work-contract.md)를 따른다.

## 1. 다시 쓰기와 대입

- 요청을 「누가 · 어떤 상황에서 · 무슨 문제를 겪나」 한 문장으로 다시 쓴다. 요청에 든 방법(「알림을 넣자」)은 해결책 후보로 내린다.
- `PRODUCT.md`의 대상 사용자·핵심 문제·원칙·비목표와 대조한다. 안 맞거나 지금 풀 근거가 없으면 보류를 권장하고 이유를 보인 뒤 멈춘다. `PRODUCT.md`가 없으면 「방향 문서 없음」을 밝히고 누구의 어떤 문제인지만 묻는다.

## 2. 근거

- 사용 기록, 인터뷰, 관찰, 피드백, 기존 PRD·`RESEARCH.md`에서 근거를 찾는다.
- **관찰**(출처·시점이 있는 사실)과 **가설**(그 해석)을 나눠 적는다. 에이전트가 만든 분석은 실제 사용자 증거가 아니라고 표시한다.
- 근거가 모자라면 무엇을 어떻게 모을지 제안한다. 원자료가 남아야 하는 수집이면 시장 조사 스킬(`market-research`)이 맡는다고 알린다.

## 3. 해결책과 가정

- 해결책 후보를 둘 이상 비교한다: 무엇을 얻고 잃나, 구현 비용, 틀렸을 때의 비용.
- 틀렸을 때 선택이 가장 크게 바뀌는 가정 하나를 고른다.

## 4. PRD 초안

```bash
python3 <이 플러그인>/scripts/d3_scaffold.py feature <feature> --root <프로젝트>
```

Purpose·Problem(관찰과 가설)·Solution(후보와 지금의 선택)·Non-goals·Success Criteria 후보·Rationale(남은 위험)을 채운다. 기존 조사·디자인은 다시 쓰지 않고 References에 링크한다. 이미 있는 PRD면 바뀐 칸만 고친다.

## 5. 다음 활동 판정

| 조건 | 판정 | 다음을 맡는 곳 |
|---|---|---|
| 방향에 안 맞거나 근거가 없음 | 보류. 이유를 Rationale에 | — |
| 결정을 바꿀 가정이 확인되지 않음 | 실험 | `validate-hypothesis` |
| 해결책·작은 구현 범위·성공 판단 방법을 설명할 수 있음 | 구현 | `deliver-work` |

판정과 근거를 보이고 사람이 고르게 한다. 화면 방향이 갈리는 가정이면 시안 비교(`compare-mockups`)가 가장 싼 확인 방법인지 함께 제안한다.

```bash
python3 <이 플러그인>/scripts/check_d3_docs.py --root <프로젝트>
```
