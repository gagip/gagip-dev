---
name: notion-knowledge
description: >
  Notion Knowledge DB에서 도메인 규칙, 패턴, 방법론을 검색해 반환하는 스킬.
  다음 상황에서 반드시 이 스킬을 사용할 것:
  - 사용자가 "지식 베이스 검색해줘", "knowledge 찾아줘", "search-knowledge"라고 말할 때
  - 코딩 패턴, 아키텍처 결정, 개발 가이드라인이 필요한 코드 작업을 시작할 때
    (예: Android 코드 작성, 테스트 코드 작성, 아키텍처 설계 등)
  - 특정 기술의 컨벤션이나 베스트 프랙티스가 궁금할 때
  Knowledge DB에 없으면 Obsidian 볼트를 대안으로 검색한다.
allowed-tools: mcp__claude_ai_Notion__fetch, mcp__claude_ai_Notion__search, Read, Bash
argument-hint: (선택) 검색 키워드 또는 주제. 생략 시 현재 작업 맥락에서 자동 파악
---

# Search Knowledge 스킬

Notion Knowledge DB에서 도메인 지식을 검색해 작업에 활용한다.  
Knowledge DB가 비어있거나 결과가 없으면 Obsidian 볼트를 대안으로 검색한다.

## Knowledge DB 정보

- **DB 페이지 URL**: `$NOTION_KNOWLEDGE_DS_ID`
- **위치**: HappySealStudio > Knowledge

## Obsidian 볼트 대안 경로

- `/Volumes/OneTouch/workspace/gagip-obsidian/wiki/`
- 하위 폴더: `topics/dev-guidelines/`, `topics/architecture/`, `topics/basic/`, `topics/android/` 등

---

## 실행 절차

### Step 1: Data Source ID 결정

```bash
DS_ID="$NOTION_KNOWLEDGE_DS_ID"
echo $DS_ID
```

### Step 2: 검색 키워드 파악

인자로 키워드가 주어지면 그것을 사용한다.  
없으면 현재 대화 맥락에서 검색할 키워드를 추출한다.  
예: Android 코드 작업 중이면 "android kotlin conventions", 테스트 작성 중이면 "test guidelines"

### Step 3: Knowledge DB 검색

`mcp__claude_ai_Notion__search`로 키워드를 검색한다.  
결과 중 Knowledge DB(`$NOTION_KNOWLEDGE_DS_ID`) 하위 페이지만 필터링한다.

관련도 높은 항목을 최대 5개까지 추린다.

### Step 4: 결과 처리

**결과 있음 → Step 5 (Notion 내용 확인)**  
**결과 없음 → Step 6 (볼트 대안 검색)**

### Step 5: Notion 내용 확인 및 요약

`mcp__claude_ai_Notion__fetch`로 각 항목의 내용을 읽는다.  
현재 작업에 직접 관련된 핵심 내용만 추출해 요약한다.  
관련 없는 항목은 포함하지 않는다.

### Step 6: Obsidian 볼트 대안 검색

Knowledge DB에 결과가 없으면 Obsidian 볼트 wiki 폴더를 검색한다.

```bash
grep -r "<키워드>" /Volumes/OneTouch/workspace/gagip-obsidian/wiki/ -l --include="*.md"
```

관련 파일이 있으면 `Read`로 내용을 읽어 요약한다.  
없으면 해당 지식이 없다고 사용자에게 알린다.

---

## 결과 출력 형식

```
📚 Knowledge 검색 결과: "<키워드>"

출처: Notion Knowledge DB / Obsidian 볼트

[항목명]
- 핵심 내용 요약
- 현재 작업 적용 포인트
```

결과가 없을 때:
```
"<키워드>" 관련 항목이 없습니다.
Knowledge DB에 추가하시겠습니까?
```

---

## 행동 원칙

- 검색 결과는 참고 자료다 — 현재 프로젝트 맥락에 맞게 적용 여부를 판단한다
- Knowledge DB가 현재 비어있을 수 있으므로, Notion 검색 실패 시 바로 볼트를 확인한다
- 결과가 없어도 작업을 중단하지 않는다
