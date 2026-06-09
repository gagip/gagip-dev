---
name: notion-context
description: >
  현재 대화에서 결정된 내용을 Notion Context DB의 해당 프로젝트 페이지에 반영하는 스킬.
  다음 상황에서 반드시 이 스킬을 사용할 것:
  - 사용자가 "컨텍스트 업데이트해줘", "결정사항 저장해줘", "context 반영해줘", "update-context"라고 말할 때
  - 대화 중 기술 스택 선택("JWT로 가자", "React 쓰기로 함"), 기능 범위 변경("모바일은 빼자"),
    아키텍처 방향 결정("레이어드 아키텍처로"), 제약사항 확정 등 명시적 결정이 내려졌을 때
  결정이 내려진 직후 자동으로 실행하는 것이 기본이며, 사용자가 명시적으로 요청할 때도 실행한다.
allowed-tools: mcp__claude_ai_Notion__fetch, mcp__claude_ai_Notion__search, mcp__claude_ai_Notion__notion-create-pages, mcp__claude_ai_Notion__notion-update-page
argument-hint: (선택) 프로젝트명. 생략 시 대화 맥락에서 자동 파악
---

# Update Context 스킬

대화에서 내려진 결정을 Notion Context DB에 누적 반영해, 다음 세션에서도 AI가 프로젝트 맥락을 이어받을 수 있게 한다.

## Context DB 정보

- **DB 페이지 URL**: `$NOTION_CONTEXT_DS_ID`
- **위치**: HappySealStudio > Context

---

## 실행 절차

### Step 1: Data Source ID 결정

```bash
DS_ID="$NOTION_CONTEXT_DS_ID"
echo $DS_ID
```

### Step 2: 프로젝트명 파악

인자로 프로젝트명이 주어진 경우 그것을 사용한다.  
없으면 대화 맥락(현재 작업 디렉터리, 언급된 프로젝트명)에서 파악한다.  
그래도 불명확하면 사용자에게 묻는다.

### Step 3: 결정 내용 추출

현재 대화를 분석해 저장할 가치가 있는 결정을 추출한다.  
아래 기준에 해당하는 것만 추출한다 — 미결 논의나 단순 질문은 제외:

| 유형 | 예시 |
|------|------|
| 기술 결정 | "JWT로 인증 구현", "Kotlin 사용" |
| 범위 결정 | "알림 기능은 v2로 이관", "다크모드 포함" |
| 아키텍처 결정 | "VSA 패턴 적용", "단방향 데이터 흐름" |
| 제약사항 | "오프라인 지원 필수", "응답 시간 1초 이내" |
| 열린 질문 해소 | 이전 미결 사항이 이번 대화에서 결정됨 |

추출 결과가 없으면 사용자에게 알리고 종료한다.

### Step 4: Context DB에서 프로젝트 검색

`mcp__claude_ai_Notion__search`로 프로젝트명을 검색한다.  
검색 결과 중 Context DB(`$NOTION_CONTEXT_DS_ID`)의 하위 페이지인 것을 찾는다.

- 해당 페이지 발견 → Step 5
- 없음 → Step 5

### Step 5: 기존 페이지 업데이트

`mcp__claude_ai_Notion__fetch`로 페이지 내용을 읽어 현재 구조를 파악한다.

결정 내용을 해당 섹션에 bullet로 추가한다 (기존 내용은 건드리지 않고 누적):

| 결정 유형 | 추가 위치 |
|-----------|-----------|
| 기술 결정, 아키텍처 결정 | `## 기술 결정사항` |
| 범위 추가 | `## 범위 > In` |
| 범위 제외 | `## 범위 > Out` |
| 제약사항, 요구사항 | `## 핵심 요구사항` |
| 열린 질문 해소 | `## 열린 질문`에서 해당 항목 제거 |

각 bullet 형식: `- (YYYY-MM-DD) 결정 내용`

`mcp__claude_ai_Notion__notion-update-page`로 페이지 본문과 `마지막 갱신` 속성을 오늘 날짜로 업데이트한다.

### Step 6: 새 프로젝트 항목 생성

`mcp__claude_ai_Notion__notion-create-pages`로 Context DB에 새 페이지를 생성한다.  
parent는 Context DB (`$NOTION_CONTEXT_DS_ID`).

페이지 본문 초기 템플릿:

```
## 프로젝트 개요

## 핵심 요구사항

## 기술 결정사항

## 범위
### In
### Out

## 열린 질문
```

생성 후 Step 4의 업데이트 절차를 진행한다.

---

## 완료 메시지

```
✅ Context 업데이트 완료

- 프로젝트: <프로젝트명>
- 반영된 결정:
  - <결정1>
  - <결정2>
```
