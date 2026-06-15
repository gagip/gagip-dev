---
name: create-ppt
description: >
  개발 진행 현황 브리핑용 HTML 프레젠테이션을 자동으로 생성하는 스킬.
  Claude가 HTML을 직접 쓰지 않고 번들된 Python 스크립트에 위임하므로
  토큰 비용이 최소화되고 항상 동일한 미니멀 흑백 디자인이 보장된다.
  "PPT 만들어줘", "발표자료 만들어", "브리핑 자료 생성해", "개발 현황 PPT",
  "클라이언트 발표자료", "프로젝트 소개 슬라이드 만들어", "고객 브리핑 준비해줘",
  "진행 현황 보고서 슬라이드" 같은 표현이 나오면 반드시 이 스킬을 사용한다.
  개발자가 고객/외부 파트너에게 개발 현황이나 프로그램을 브리핑하는 상황에 특히 적합하다.
allowed-tools: Bash, Write, AskUserQuestion
argument-hint: (선택) 프로젝트명 또는 주제
---

# 개발 브리핑 PPT 생성 스킬

고객 브리핑용 HTML 프레젠테이션(1920×1080)을 만드는 스킬이다.  
Claude는 내용을 JSON으로 수집하고 스크립트를 실행하기만 한다 — HTML 작성은 전혀 없다.

슬라이드는 **컴포넌트 조립** 방식으로 동작한다:
- JSON의 `slides` 배열로 어떤 슬라이드를 어떤 순서로 넣을지 Claude가 결정한다.
- `slides`를 생략하면 **기본 18장 프리셋**이 자동 사용된다.
- 같은 타입을 여러 번 배치하거나 불필요한 슬라이드를 제거하는 것이 자유롭다.

---

## 컴포넌트 카탈로그

| type | 슬라이드 | 인라인 데이터 키 |
|------|----------|-----------------|
| `cover` | 표지 | `subtitle` |
| `toc` | 목차 (섹션 슬라이드에서 자동 생성) | (없음) |
| `section` | 섹션 구분 | `title`, `subtitle` |
| `overview` | 프로젝트 개요 | `summary`, `detail`, `period`, `scope`, `team`, `status` |
| `background` | 추진 배경 | `points[3]` |
| `features` | 핵심 기능 카드 | `items[{id, name, desc, highlight}]` |
| `roadmap` | 개발 진행 현황 | `phases[{label, name, status}]`, `progress_pct` |
| `metrics` | 주요 성과 지표 | `items[{value, unit, name, note}]` |
| `architecture` | 시스템 아키텍처 | `layers[{label, name, highlight?}]` |
| `tech_stack` | 기술 스택 | `items[{category, stack}]` |
| `implementation` | 구현 상세 | `description`, `points[]`, `code` |
| `schedule` | 일정 및 산출물 | `items[{phase, deliverables, period, status}]` |
| `before_after` | 도입 전후 비교 | `before[]`, `after[]` |
| `impact` | 기대 효과 (전면 텍스트) | `text` |
| `next_steps` | 다음 단계 | `steps[{name, deadline}]` |
| `closing` | 마무리 | `contact` |

> **`status` 허용값**: `"완료"` | `"진행 중"` | `"예정"`  
> **`highlight: true`**: `features.items`에서 정확히 1개, `architecture.layers`에서 최대 1개

---

## 실행 흐름

### 1단계: 정보 수집

AskUserQuestion으로 핵심 정보를 한 번에 물어본다.
부족한 항목은 최대 1회 추가 질문한다. 모든 항목은 선택사항이다.

**핵심 질문 (필수)**
- 프로젝트명은 무엇인가요?
- 발표 날짜와 발표자 정보는? (예: `2026.06 / 홍길동 · (주)ABC`)
- 프로젝트를 한두 문장으로 설명해 주세요. (배경, 목적, 현재 상태)

**선택 질문 (더 풍부한 슬라이드를 원할 때)**
- 개발 단계(기획/개발/테스트/배포)별 진행 현황은?
- 핵심 기능 3가지는?
- 숫자로 보여줄 성과 지표(예: 응답속도, 커버리지)가 있나요?
- 기술 스택은?
- 도입 전후 비교할 수 있는 내용이 있나요?
- 다음 단계 계획은?

### 2단계: JSON 구성 및 저장

수집한 내용을 아래 구조의 JSON으로 구성해 `/tmp/ppt_content.json`에 저장한다.

**JSON 구조 핵심 원칙**
- `slides` 배열에 원하는 슬라이드 타입과 순서를 직접 지정한다.
- 각 슬라이드 객체에 데이터를 인라인으로 포함한다.
- `project_name`, `date`, `presenter`는 top-level에 두면 모든 슬라이드가 공유한다.
- 정보가 없는 슬라이드는 포함하지 않거나, 포함 시 데이터 키를 생략하면 기본값이 사용된다.
- **절대 정보를 임의로 지어내지 않는다.**

```json
{
  "project_name": "프로젝트명",
  "date": "2026.06",
  "presenter": "발표자 · 소속",

  "slides": [
    {
      "type": "cover",
      "subtitle": "개발 진행 현황과 핵심 기능을 고객에게 브리핑하기 위한 발표 자료"
    },
    { "type": "toc" },
    {
      "type": "section",
      "title": "프로젝트 개요",
      "subtitle": "배경과 목표, 핵심 기능"
    },
    {
      "type": "overview",
      "summary": "한 문단 요약 (목적과 범위)",
      "detail": "핵심 가치 또는 차별점",
      "period": "2026.01 – 2026.06",
      "scope": "웹 · API · 관리자",
      "team": "개발 4 · 디자인 1",
      "status": "진행 중"
    },
    {
      "type": "background",
      "points": [
        "기존 방식의 한계나 고객이 겪던 문제",
        "새로운 접근이 필요한 이유",
        "이 프로젝트가 해결하는 방향"
      ]
    },
    {
      "type": "features",
      "items": [
        {"id": "F-01", "name": "기능명", "desc": "가치 설명", "highlight": false},
        {"id": "F-02", "name": "기능명", "desc": "가치 설명", "highlight": false},
        {"id": "F-03", "name": "핵심 기능", "desc": "가장 중요한 기능", "highlight": true}
      ]
    },
    {
      "type": "section",
      "title": "개발 현황",
      "subtitle": "진행 현황과 성과"
    },
    {
      "type": "roadmap",
      "phases": [
        {"label": "PHASE 1", "name": "기획 · 설계", "status": "완료"},
        {"label": "PHASE 2", "name": "핵심 개발",   "status": "완료"},
        {"label": "PHASE 3", "name": "테스트",       "status": "진행 중"},
        {"label": "PHASE 4", "name": "배포",          "status": "예정"}
      ],
      "progress_pct": 62.5
    },
    {
      "type": "metrics",
      "items": [
        {"value": "98", "unit": "%",  "name": "테스트 커버리지", "note": "목표 95% 초과"},
        {"value": "120","unit": "ms", "name": "평균 응답 시간",  "note": "40% 단축"},
        {"value": "24", "unit": "개", "name": "완료된 기능",     "note": "전체 32개 중"}
      ]
    },
    {
      "type": "architecture",
      "layers": [
        {"label": "CLIENT",  "name": "웹 · 앱"},
        {"label": "GATEWAY", "name": "API 서버"},
        {"label": "CORE",    "name": "비즈니스 로직", "highlight": true},
        {"label": "DATA",    "name": "DB · 캐시"}
      ]
    },
    {
      "type": "tech_stack",
      "items": [
        {"category": "FRONTEND",  "stack": "React · TypeScript · Vite"},
        {"category": "BACKEND",   "stack": "Node.js · Express"},
        {"category": "DATABASE",  "stack": "PostgreSQL · Redis"},
        {"category": "INFRA",     "stack": "Docker · AWS · CI/CD"}
      ]
    },
    {
      "type": "section",
      "title": "상세 & 일정",
      "subtitle": "구현 방식과 일정"
    },
    {
      "type": "implementation",
      "description": "핵심 로직 동작 방식",
      "points": ["처리 흐름 포인트 1", "포인트 2", "포인트 3"],
      "code": "// 핵심 처리 예시\nasync function process(req) {\n  return transform(await fetch(url));\n}"
    },
    {
      "type": "schedule",
      "items": [
        {"phase": "기획",   "deliverables": "요구사항 · 설계",   "period": "2026.01–02", "status": "완료"},
        {"phase": "개발",   "deliverables": "핵심 기능 · API",   "period": "2026.03–05", "status": "완료"},
        {"phase": "테스트", "deliverables": "통합 테스트 · QA",  "period": "2026.06",    "status": "진행 중"},
        {"phase": "배포",   "deliverables": "운영 배포 · 인수인계", "period": "2026.07", "status": "예정"}
      ]
    },
    {
      "type": "before_after",
      "before": ["수작업 처리", "느린 속도", "파편화된 데이터"],
      "after":  ["자동화 파이프라인", "40% 빨라진 속도", "통합 데이터 흐름"]
    },
    {
      "type": "impact",
      "text": "이 프로젝트로 고객이 얻는 가장 큰 가치를 한 문장으로 정리합니다."
    },
    {
      "type": "next_steps",
      "steps": [
        {"name": "통합 테스트 완료 및 QA",       "deadline": "~ 2026.06"},
        {"name": "운영 환경 배포 및 안정화",      "deadline": "~ 2026.07"},
        {"name": "인수인계 및 운영 가이드 전달",  "deadline": "2026.07"}
      ]
    },
    {
      "type": "closing",
      "contact": "이름 · 이메일"
    }
  ]
}
```

**슬라이드를 줄이고 싶을 때**: `slides` 배열에서 불필요한 항목을 제거한다.  
예) 기술 스택 정보 없음 → `tech_stack` 슬라이드 제거.  
예) 짧은 소개 자료 → `cover` → `section` → `overview` → `features` → `closing` 5장만 구성.

### 3단계: 스크립트 실행

이 SKILL.md 파일의 위치를 기반으로 스크립트 경로를 결정한다.

```bash
# 스킬 디렉터리 경로 (이 파일과 같은 위치)
SKILL_DIR="/Volumes/OneTouch/workspace/gagip-dev/plugins/common/skills/create-ppt"

# 출력 파일명: 프로젝트명_브리핑.html (또는 사용자 지정)
OUTPUT_FILE="${PROJECT_NAME}_브리핑.html"

python3 "$SKILL_DIR/scripts/generate_ppt.py" \
  --input /tmp/ppt_content.json \
  --output "$OUTPUT_FILE"
```

성공 시 출력:
```
✓ 생성 완료: /path/to/파일.html
  슬라이드: N장 | 크기: XXkB
```

### 4단계: 결과 보고

출력 파일 경로를 알려주고 다음을 안내한다:
- 브라우저에서 열면 바로 발표 가능 (키보드 `←` `→` `Space` 네비게이션, `F` 전체화면)
- 텍스트 수정이 필요하면 HTML 파일을 직접 열어 편집하거나, JSON을 수정 후 스크립트를 재실행
- 슬라이드 구성을 바꾸고 싶으면 `slides` 배열을 수정 후 재실행

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `ValueError: 알 수 없는 슬라이드 type` | type 오타 | 컴포넌트 카탈로그 표에서 정확한 type 확인 |
| `ModuleNotFoundError` | Python 경로 문제 | `python3` 대신 `python` 시도 |
| 폰트 깨짐 | 오프라인 환경 | 인터넷 연결 후 다시 열기 |
| 슬라이드가 흰색 | 스크립트 오류 | JSON 형식 확인 후 재실행 |
