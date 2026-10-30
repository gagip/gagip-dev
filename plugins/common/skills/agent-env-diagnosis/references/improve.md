# 3단계 개선

이 스킬은 개선 후보표를 만들고 사용자 선택을 받는 데까지 한다. 반영은 기존 절차로 넘긴다.

## 1. 후보표 보이기

`aggregate.py`가 `report_data.json`의 `candidates`에 기준을 넘은 항목을 넣는다. HTML 6절이 그 표다.

| 재료 | 기준 | 할 일 | 넘길 곳 |
|---|---|---|---|
| 교정이 몰린 칸 (업무·단계·종류) | 3건 이상 | 그 단계를 맡는 스킬 본문·지침 문장 | `retrospective` |
| 규칙이 있었는데 어김 | 같은 규칙 2건 이상 | 안 읽혔으면 자리 옮기기, 읽혔는데 어겼으면 훅·검사 스크립트 | `retrospective` |
| 규칙이 없던 반복 실수 | 같은 종류 2건 이상 | 새 규칙 초안 또는 새 스킬 | `retrospective` / `build-skill` |
| 스킬 안 부름 | 같은 스킬 2건 이상 | 스킬 설명(켜지는 말)·앞 단계 스킬의 다음 단계 안내 | `retrospective` |
| 안 읽히는 상세 파일 | 연 세션 2개 이하 | 읽기를 스킬 첫 단계로, 또는 필요한 줄을 스킬 본문으로 | `retrospective` |
| 안 열리는 메모리 | 1개 이상 | 보관·병합 후보 고르기 | `consolidate-memory` |
| 상시 지침 크기 | 항상 | 어긴 적 없고 다른 곳에서 막히는 규칙을 상세 파일로 | `retrospective` |

후보마다 근거 교정 인용문 2~3개(`corrections.json`)를 붙여 대화창에 보이고, 사용자가 고르게 한다. 하나도 고르지 않으면 여기서 끝낸다.

## 2. 넘기기

- 지침·스킬 수정: `retrospective`를 열어 고른 후보를 업데이트 후보로 넘긴다. 후보 검증(`retro-verifier`) → 사용자 확인 → 반영은 그 스킬이 한다.
- 메모리 정리: `consolidate-memory`에 안 열린 파일 목록(`report_data.json`의 `env.memory_never_files`)을 넘긴다.
- 새 스킬: `build-skill`.

이 스킬이 SKILL.md·지침·메모리를 직접 고치지 않는다.

## 3. 기준값 남기기

`aggregate.py`가 쓴 `baseline.json`(업무·단계·종류 칸별 세션당 교정 수)을 기준값 폴더에 날짜를 붙여 복사한다.

```bash
cp "<out-dir>/baseline.json" "<기준값 폴더>/baseline_<YYYY-MM-DD>.json"
```

다음 진단 때 `aggregate.py --baseline <그 파일>`로 넘기면 HTML 6절 아래에 칸별 전/후가 나온다. 반영한 항목의 칸이 줄었는지 이 표로 본다.
