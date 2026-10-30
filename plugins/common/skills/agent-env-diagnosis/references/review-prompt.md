# 독립 검토자 지시문

분류·재판정을 하지 않은 서브에이전트 하나에게 넘긴다. `{OUT}`·`{TAXONOMY}`를 바꿔 넣는다.

```
자동 분류 결과가 원본과 맞는지 표본으로 검증한다. 읽기 전용이다. 원본·분류 파일을 고치지 말고, git 명령을 실행하지 않는다. 쓰는 파일은 아래 두 개다. 도구 호출은 70회 안팎에서 멈추고, 넘으면 그때까지의 부분 결과를 보고한다.

대상: {OUT}
- corrections.json: 진짜 교정으로 판정된 항목(session, date, quote, stage, kind, cause, rule_place, rule_file, what).
- classified/chunk_*.json: 세션별 업무 종류·단계.
- sessions.jsonl: 세션 키 → 원본 기록 경로(path). .zst 는 `zstd -dc <경로>` 로 읽는다.
- 기준: {TAXONOMY}

표본은 python3 random.seed(<오늘 날짜 숫자>)로 뽑고 뽑은 키를 보고에 적는다.
A. corrections.json 30건: 원본에서 그 발화와 바로 앞 에이전트 응답을 찾아 (1) 진짜 교정인지 (2) kind (3) stage (4) cause 가 맞는지 판정한다. cause 가 규칙있음_어김이면 rule_file 에 그 규칙이 실제로 있는지 본다.
B. classified 세션 25개(automated 가 평가인 세션 제외): 원본 사용자 발화를 훑어 work_type 이 맞는지 판정한다.
C. 각 일치율과 틀린 유형의 경향을 정리한다.

출력 1: {OUT}/review.md — 읽은 원본 파일 수, 표본 키, 건별 판정과 근거 한 줄, 일치율, 경향.
출력 2: {OUT}/review.json — {"sample_rows": [[무엇을, 결과, 뜻], ...]} (A의 네 항목과 B, 결과는 "24/30 (80%)" 꼴).
마지막 답변: 일치율과 가장 큰 오류 경향 두 가지를 5줄 이내.
```

검토자가 돌려준 뒤 메인 세션이 `review.json`에 `method`(센 방법)·`limits`(한계)·`decide`(사용자가 정할 것) 배열을 더한다.
