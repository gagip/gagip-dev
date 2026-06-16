---
name: memory-curator
description: |
  대화 세션에서 유의미한 정보/패턴을 메모리에 즉시 저장하고, 쌓인 메모리를 주기적으로 정리하는 스킬.
  
  두 가지 모드로 동작한다:
  - 기본 모드 (`/memory-curator`): 현재 세션 JSONL을 분석해 놓친 메모리를 추출하고 저장
  - 리뷰 모드 (`/memory-curator review`): 전체 메모리 파일을 정리하고 CLAUDE.md 승격 후보 및 문서화 대상 제안
  
  다음 표현이 나오면 반드시 이 스킬을 사용할 것:
  "메모리 정리해줘", "세션 메모리 저장해줘", "memory curator", "메모리 큐레이션",
  "메모리 리뷰", "memory review", "지침 정리해줘", "문서화할 거 추려줘",
  "이번 세션 메모리", "놓친 메모리 있어?", "메모리 업데이트해줘"
---

# memory-curator

## 모드 판별

인자가 없으면 **기본 모드**, `review` 인자가 있으면 **리뷰 모드**로 실행한다.

---

## 기본 모드: 세션 메모리 추출 및 저장

> **retrospective와의 관계**: 이 기본 모드는 `retrospective` 회고가 넘긴 메모리 후보를 받는 **단일 관문**이기도 하다. retrospective는 "무엇을 어디에 남길지"(볼트·스킬·문서화·CLAUDE.md)를 넓게 분배하고, 그중 **메모리는 여기로 위임**한다. 직접 호출되든 retrospective에서 이어지든 절차는 같다 — 핵심은 아래 4번 **중복 방지 필터**로 메모리가 비대해지지 않게 막는 것이다.

### 1. 현재 세션 JSONL 파일 찾기

```bash
# 현재 작업 디렉토리로 프로젝트 슬러그 계산
# 예: /Users/gagip/workspace/voltera/vibe-voltera-wearable-issue18
# → -Users-gagip-workspace-voltera-vibe-voltera-wearable-issue18
cwd=$(pwd)
slug=$(echo "$cwd" | sed 's|/|-|g' | sed 's|^-||')
project_dir="$HOME/.claude/projects/$slug"

# 가장 최근 JSONL 파일
ls -t "$project_dir"/*.jsonl 2>/dev/null | head -1
```

### 2. 세션 내용 추출

JSONL에서 `type=user`와 `type=assistant` 메시지를 읽어 대화 흐름을 파악한다.

```bash
python3 - <<'EOF'
import json, sys
path = "<위에서 찾은 JSONL 경로>"
lines = [json.loads(l) for l in open(path)]
for l in lines:
    if l.get('type') in ('user', 'assistant'):
        role = l['type']
        content = l.get('message', {}).get('content', '')
        if isinstance(content, list):
            text = ' '.join(c.get('text','') for c in content if c.get('type')=='text')
        else:
            text = str(content)
        if text.strip() and not text.startswith('<system-reminder'):
            print(f"[{role}] {text[:300]}")
EOF
```

### 3. 기존 메모리 파일 읽기

```bash
memory_dir="$HOME/.claude/projects/$slug/memory"
cat "$memory_dir/MEMORY.md" 2>/dev/null
# 각 메모리 파일도 필요 시 읽기
```

전역 메모리도 확인:
```bash
ls "$HOME/.claude/memory/" 2>/dev/null
```

### 4. 저장할 항목 추출 기준

세션 내용을 분석해 아래 기준으로 메모리 후보를 판단한다.

**저장하는 것 (메모리 타입별)**

| 타입 | 저장 기준 |
|------|-----------|
| `feedback` | 사용자가 접근 방식을 수정했거나 ("아니면", "그게 낫다", "그렇게 하지 마"), 명시적으로 확인한 비자명한 선택 |
| `project` | 새로 알게 된 마감일, 의사결정 배경, 이해관계자 요구사항 |
| `user` | 사용자의 역할/전문성/선호에 대해 새로 알게 된 사실 |
| `reference` | 외부 시스템 위치, 대시보드 URL, 이슈 트래커 링크 |

**저장하지 않는 것 — 중복 방지 필터 (이 스킬의 핵심 역할)**

메모리의 가치는 "많이 쌓는 것"이 아니라 "다음에 행동을 바꿀 것만 남기는 것"이다. 아래에 걸리면 거른다. 빈손("이번 세션에서 추가할 메모리 없음")이 오히려 건강한 신호다 — 새로 줍는 것보다 이미 있는 것을 거르는 게 이 스킬의 본질이다.

- **코드에 있음**: 코드 패턴, 파일 경로, 아키텍처 → 코드가 단일 소스
- **git에 있음**: 히스토리, 최근 변경 → git log로 확인 가능
- **PR/커밋에 있음**: 이번 작업의 구현 세부사항
- **이미 메모리에 있음**: 기존 메모리 파일과 중복 (3번에서 읽은 MEMORY.md로 대조)
- **CLAUDE.md(항상 로드)에 있음**: 전역/프로젝트 CLAUDE.md에 이미 있는 규칙은 메모리로 중복 보유하지 않는다

### 5. 메모리 파일 저장

신규 항목마다 아래 형식으로 파일 생성:

```markdown
---
name: kebab-case-slug
description: 한 줄 요약 — MEMORY.md 인덱스에 표시될 내용
metadata:
  type: feedback|project|user|reference
---

[내용]

**Why:** [이유 — feedback/project 타입에 필수]

**How to apply:** [적용 시점 — feedback/project 타입에 필수]
```

저장 위치:
- 현재 프로젝트 관련: `~/.claude/projects/<slug>/memory/<name>.md`
- 프로젝트 무관한 user/feedback: `~/.claude/memory/<name>.md`

MEMORY.md 인덱스에 한 줄 추가:
```markdown
- [제목](파일명.md) — 한 줄 훅
```

### 6. 보고

저장한 항목과 이유를 사용자에게 간결하게 보고한다. 저장한 것이 없으면 "이번 세션에서 추가할 메모리 항목이 없습니다"라고 말한다.

---

## 리뷰 모드: 전체 메모리 정리

### 1. 모든 메모리 파일 읽기

```bash
slug=$(pwd | sed 's|/|-|g' | sed 's|^-||')
ls ~/.claude/projects/$slug/memory/*.md 2>/dev/null
ls ~/.claude/memory/*.md 2>/dev/null
```

각 파일의 frontmatter와 본문을 읽어 전체 메모리 목록을 파악한다.

### 2. 정리 항목 식별

다음 항목을 찾는다:

- **중복**: 같은 규칙을 다른 파일에서 반복하는 경우
- **상충**: 서로 모순되는 피드백 (최신 것이 우선)
- **만료**: project 타입 중 날짜가 지난 마감일, 완료된 이슈
- **병합 가능**: 같은 주제의 여러 feedback을 하나로 합칠 수 있는 경우

정리 대상 목록을 사용자에게 보여주고 **확인을 받은 후** 실행한다.

### 3. CLAUDE.md 승격 후보 제안

여러 feedback 메모리에서 반복되는 패턴이 보이면 CLAUDE.md에 추가할 전역 지침 후보로 제안한다.

형식:
```
## CLAUDE.md 승격 후보

다음 패턴이 여러 세션에서 반복됩니다. 전역 지침으로 추가하시겠습니까?

1. **[규칙 요약]**
   - 근거: [관련 메모리 파일 목록]
   - 제안 문구: "[CLAUDE.md에 추가할 내용]"
```

### 4. 문서화 후보 추출

project/reference 타입 메모리 중 노션 문서로 정리할 만한 내용을 추출해 초안을 제시한다.

형식:
```markdown
## 노션 초안: [주제]

### 배경
[왜 이 작업을 했는지]

### 결정 사항
[주요 의사결정과 근거]

### 관련 링크
[PR, 이슈, 참고 문서]
```

---

## 주의사항

- 메모리 파일 삭제/수정은 반드시 사용자 확인 후 실행
- MEMORY.md는 200줄 제한이 있으므로 인덱스 항목은 한 줄로 간결하게 유지
- 기존 메모리와 중복 여부를 저장 전에 반드시 확인
