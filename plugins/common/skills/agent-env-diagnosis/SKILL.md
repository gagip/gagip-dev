---
name: agent-env-diagnosis
description: >
  Claude Code·Codex 세션 기록으로 에이전트 환경(스킬·지침·상세 파일·메모리·훅·서브에이전트)이
  얼마나 쓰이고 어디서 실수가 나는지 재고, 고칠 곳을 골라 기존 반영 절차로 넘긴다. 빠른 측정 →
  진단 → 개선 3단계이고 기본은 빠른 측정만 한다. "스킬 사용 지표", "어떤 스킬 자주 써", "스킬
  도달률", "메모리 얼마나 읽혀", "지침 너무 길어?", "업무 파이프라인", "실수 분석", "에이전트 환경
  진단", "개선할 곳 골라줘"에 반드시 사용한다. 한 세션·짧은 기간의 교훈 반영은 `retrospective`,
  메모리 병합은 `consolidate-memory`, 새 스킬 제작은 `build-skill`이 맡는다.
allowed-tools: Bash, Read, Write, Agent
argument-hint: (선택) 단계와 기간 — "진단 30" , "개선", "2026-08-01". 생략 시 빠른 측정 14일
---

# agent-env-diagnosis

세션 기록에서 에이전트 환경이 실제로 어떻게 쓰이는지 잰다. 무엇을 셀지는 스크립트가 정하고,
판단이 필요한 분류만 서브에이전트가 한다. 기록 원본을 메인 컨텍스트에서 직접 읽지 않는다.

`<스킬>`은 이 `SKILL.md`가 있는 폴더다. 산출물 폴더 `<out>`은 사용자가 정한 곳, 없으면 환경변수
`AGENT_ENV_DIAGNOSIS_DIR` 아래 `<YYYY-MM-DD>_<단계>/`, 그것도 없으면 사용자에게 묻는다. 교정 인용문이
들어가므로 공개 레포 안에 두지 않는다.

## 기록 위치

| 도구 | 위치 | 비고 |
|---|---|---|
| Claude Code | `${CLAUDE_CONFIG_DIR:-~/.claude}/projects/*/*.jsonl` | 하위 세션(`subagents/`)은 제외 |
| Codex | `${CODEX_HOME:-~/.codex}/sessions/**`, `archived_sessions/*.jsonl(.zst)` | 하위 세션(`session_meta.source.subagent`)은 제외. `.zst`는 `zstd` 명령이 없으면 건너뛰고 개수를 결과 맨 위에 적는다 |

모든 스크립트는 `--source all|claude|codex`(기본 all)로 고른다. Codex는 스킬 호출이 따로 기록되지
않아 도구 호출 인자에 나온 `skills/<이름>/SKILL.md`로 센다.

## 단계 고르기

| 사용자 말 | 단계 |
|---|---|
| 지표·도달률·자주 쓰는 스킬·메모리·지침 크기 | 1단계만 |
| 업무 파이프라인·실수 분석·진단 | 1 → 2단계 |
| 개선할 곳·고칠 곳 | 2단계 결과가 있으면 3단계, 없으면 2 → 3 |

2단계는 30일 기준 서브에이전트 10개 안팎과 수십만 토큰이 든다. 시작 전에 기간·예상 묶음 수를 한 줄로 알린다.

---

## 1단계 · 빠른 측정

```bash
python3 "<스킬>/scripts/measure.py" --days 14            # 스킬·서브에이전트
python3 "<스킬>/scripts/env_scan.py" --days 14 \
  --always <지금 실린 지침 파일...> --details <상세 파일 폴더...> --memory <메모리 폴더>
```

`env_scan.py`에 넘길 경로는 `references/env-assets.md`대로 찾는다. 인자가 숫자면 `--days`,
`YYYY-MM-DD`면 `--since`로 넘긴다. 결과 마크다운을 그대로 보이고, 눈에 띄는 것 세 가지를 실제
값으로 짚는다(예: "커밋 전에 읽는 상세 파일이 28세션에서 열렸고, 커밋 스킬은 91세션에서 불렸다").

## 2단계 · 진단

1. 추출: `python3 "<스킬>/scripts/extract.py" sessions --out-dir <out> --days 30`
   - 세션 레코드, 분기 세션 표시, 분류용 묶음(`chunks/chunk_NN.md`)을 만든다.
   - 스킬 평가 같은 임시 폴더 세션은 `--exclude`로 뺀다.
2. 1차 분류: 묶음마다 서브에이전트를 하나씩 한 번에 띄운다.
   - 지시문은 `references/classify-prompt.md`의 "1차 분류", 기준은 `references/taxonomy.md`다.
   - 끝나면 `python3 "<스킬>/scripts/check_chunks.py" --out-dir <out>`로 대조한다.
   - 누락이 있으면 빠진 세션만 `chunks/chunk_NNb.md`로 떼어 다시 분류하고, 결과를 `chunk_NN.json`에 합친 뒤 `b` 파일 둘을 지운다. 남의 것·중복이 있으면 그 묶음을 다시 돌린다.
3. 교정 맥락: `python3 "<스킬>/scripts/extract.py" context --out-dir <out>`
   - 교정 후보마다 앞 에이전트 응답과 그때까지 연 파일을 뽑는다.
   - 분기 세션에서 복사된 같은 인용문은 여기서 한 번만 남는다.
4. 재판정: 묶음마다 서브에이전트를 띄운다.
   - 지시문은 `references/classify-prompt.md`의 "교정 재판정"이다. 진짜 여부, 종류, 원인, 막을 규칙의 자리를 정한다.
   - 대조는 `check_chunks.py --stage judged`로 한다.
5. 환경 측정: 1단계의 `env_scan.py`를 같은 기간으로 `--json <out>/env.json`을 붙여 돌린다.
6. 집계: `python3 "<스킬>/scripts/aggregate.py" --out-dir <out> [--baseline <이전 baseline.json>]`
7. 독립 검토: 분류에 참여하지 않은 서브에이전트에게 `references/review-prompt.md`를 넘긴다.
   - 돌아오면 `review.json`에 센 방법·한계·정할 것을 더한다.
   - 그 뒤 `aggregate.py`를 다시 돌린다.
8. HTML: `python3 "<스킬>/scripts/render_html.py" --out-dir <out>`
   - 브라우저로 열어 콘솔 오류와 넘침을 확인한 뒤 사용자에게 보인다.

서브에이전트를 쓸 수 없는 하네스에서는 1차 분류를 기간을 줄여 메인 컨텍스트에서 하고, 재판정·독립 검토는
건너뛴 채 결과 맨 위에 "재판정·독립 검증 미실행"을 적는다.

## 3단계 · 개선

`references/improve.md`대로 한다.

1. HTML 6절 후보표를 근거 인용문과 함께 보이고 사용자가 고르게 한다.
2. 고른 것은 넘긴다: 지침·스킬은 `retrospective`, 메모리는 `consolidate-memory`, 새 스킬은 `build-skill`.
3. `baseline.json`을 기준값으로 남긴다.

이 스킬은 지침·스킬·메모리를 직접 고치지 않는다. 반영 규칙을 한 곳(`retrospective`)에 두기 위해서다.

---

## 한계

- 교정은 사용자 발화와 바로 앞 응답만 보고 판정한다. 세션 앞부분의 합의를 놓치면 틀린다. 독립 검토 일치율을 HTML에 함께 싣는다.
- "열었다"는 도구 호출 인자에 경로가 나온 것이라 고치려고 연 경우도 들어간다. 메모리 목록 파일이 매 세션 실리면 개별 파일이 안 열려도 쓰였을 수 있다.
- Codex 스킬 수에는 SKILL.md를 고치려고 연 경우도 들어간다.
- 같은 스킬의 다른 이름(`commit`과 `plugin:commit`)은 따로 센다.
- 20줄 이하 세션은 뺀다.
