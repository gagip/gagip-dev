---
name: notion-doctor
description: >
  Notion 워크플로우 생태계(Report/Context/Knowledge DB · 환경변수 · 볼트 폴백 경로)가
  제대로 셋업됐는지 점검하고, 누락된 항목을 구성하는 스킬.
  notion-report·notion-context·notion-knowledge·draft-plan 스킬은 이 셋업에 의존한다.
  다음 표현이 나오면 반드시 이 스킬을 사용할 것:
  "notion 셋업 점검", "notion doctor", "워크플로우 셋업 확인", "DS_ID 설정 확인",
  "notion 환경변수 점검", "notion 스킬이 안 돼", "Reports DB 연결 확인".
  새 머신 셋업 시, 또는 notion-* 스킬이 DS_ID를 못 찾아 멈출 때 사용한다.
allowed-tools: Bash, Read, Edit, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-search, mcp__claude_ai_Notion__notion-update-data-source
argument-hint: (선택) 워크플로우 부모 페이지 URL. env에 NOTION_WORKFLOW_PAGE_ID가 있으면 생략 가능
---

# Notion Doctor 스킬

`notion-report`·`notion-context`·`notion-knowledge`·`draft-plan` 스킬은 Notion DB와 환경변수에
의존한다. 이 스킬은 그 셋업을 **점검(diagnose)** 하고 누락 시 **구성(fix)** 한다.

## 점검 대상

| 항목 | 기대값 |
|------|--------|
| env `NOTION_WORKFLOW_PAGE_ID` | 3종 DB를 담은 부모 페이지 id |
| env `NOTION_REPORTS_DS_ID` | Report DB의 data source id |
| env `NOTION_CONTEXT_DS_ID` | Context DB의 data source id |
| env `NOTION_KNOWLEDGE_DS_ID` | Knowledge DB의 data source id |
| Report DB 스키마 | `제목`(title)·`유형`(select)·`상태`(select)·`요약`(text)·`프로젝트`(multi_select)·`작성일`(date) |
| Context DB 스키마 | `제목`(title)·`마지막 갱신`(date) |
| Knowledge DB 스키마 | `제목`(title) |
| 볼트 폴백 경로 | `$HOME/personal/gagip-obsidian/wiki/` 존재 |

---

## 실행 절차

### Step 1: 환경변수 점검

```bash
echo "NOTION_WORKFLOW_PAGE_ID = ${NOTION_WORKFLOW_PAGE_ID:-<unset>}"
echo "NOTION_REPORTS_DS_ID    = ${NOTION_REPORTS_DS_ID:-<unset>}"
echo "NOTION_CONTEXT_DS_ID    = ${NOTION_CONTEXT_DS_ID:-<unset>}"
echo "NOTION_KNOWLEDGE_DS_ID  = ${NOTION_KNOWLEDGE_DS_ID:-<unset>}"
```

> 환경변수는 `~/.claude/settings.json`의 `env` 블록에 설정한다. 이 블록은 Bash 툴에 즉시 주입된다.

### Step 2: 부모 페이지에서 DB 찾기 (DS_ID 미설정 시)

`NOTION_WORKFLOW_PAGE_ID`가 있으면 그 페이지를, 없으면 인자로 받은 URL(또는 사용자에게 요청)을
`notion-fetch`로 조회한다. 페이지 본문의 `<database ... data-source-url="collection://...">` 태그에서
Report/Context/Knowledge 각 DB의 data source id를 회수한다.

### Step 3: DB 존재·스키마 점검

env에 있거나 Step 2에서 회수한 각 DS_ID를 `notion-fetch`로 조회해 스키마를 확인한다.

- **Report**: `제목`·`유형`·`상태`·`요약`·`프로젝트`·`작성일` 컬럼이 모두 있는가?
- **Context**: `제목`·`마지막 갱신`이 있는가?
- **Knowledge**: `제목`(title)이 있는가?

누락 컬럼이 있으면 사용자 확인 후 `notion-update-data-source`로 보강한다:
```
ADD COLUMN "유형" SELECT('구현계획':blue, '완료보고':green, '분석':yellow, '의사결정':orange);
ADD COLUMN "상태" SELECT('초안':gray, '검토중':yellow, '완료':green);
ADD COLUMN "요약" RICH_TEXT;
ADD COLUMN "프로젝트" MULTI_SELECT('voltera':blue, 'macai':purple);
ADD COLUMN "작성일" DATE
```
title 컬럼명이 `제목`이 아니면 `RENAME COLUMN "<현재명>" TO "제목"`.

### Step 4: settings.json env 기록 (누락 시)

DS_ID/페이지 id가 env에 없으면 `~/.claude/settings.json`을 **Read**한 뒤 `env` 블록에 추가한다
(사용자 확인 후 **Edit**). 기존 키는 보존한다.
```json
"env": {
  "NOTION_WORKFLOW_PAGE_ID": "<page id>",
  "NOTION_REPORTS_DS_ID": "<report ds>",
  "NOTION_CONTEXT_DS_ID": "<context ds>",
  "NOTION_KNOWLEDGE_DS_ID": "<knowledge ds>"
}
```

### Step 5: 볼트 폴백 경로 점검

```bash
ls -d "$HOME/personal/gagip-obsidian/wiki/" >/dev/null 2>&1 \
  && echo "✅ 볼트 wiki 존재" \
  || echo "⚠️  볼트 wiki 없음: $HOME/personal/gagip-obsidian/wiki/"
```

### Step 6: 리포트

점검 결과를 항목별로 요약하고, 남은 수동 조치(있으면)를 안내한다.

```
🩺 Notion Doctor 결과

환경변수:   ✅ 4/4
Report DB:  ✅ 스키마 정합
Context DB: ✅ 스키마 정합
Knowledge:  ✅
볼트 폴백:  ✅

→ 셋업 정상. draft-plan / notion-report / notion-context / notion-knowledge 사용 가능.
```

---

## 행동 원칙

- 점검을 먼저 모두 수행하고, 구성(수정)은 누락 항목만 사용자 확인 후 진행한다.
- DB 스키마를 함부로 바꾸지 않는다 — 누락 컬럼 추가 / title rename 외의 변경은 하지 않는다.
- `settings.json` env 수정 전 항상 현재 내용을 Read해 기존 키를 보존한다.
- 회사 프로젝트 문서는 회사 Notion 워크스페이스에 둔다 (개인 워크스페이스에 회사 기밀을 저장하지 않는다).
