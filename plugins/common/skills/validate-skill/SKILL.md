---
name: validate-skill
description: >
  SKILL.md 파일의 품질을 검증하는 스킬. 새 스킬을 작성하거나 기존 스킬을 수정한 직후
  Claude가 자동으로 참조하여 필수 필드, [STOP] 패턴, allowed-tools 일관성을 점검한다.
  사용자가 직접 호출할 수 없다.
user-invocable: false
allowed-tools: Read, Glob, Grep
---

## 입력

```
$ARGUMENTS
```

`$ARGUMENTS`가 있으면 해당 경로의 SKILL.md만 검증한다.
없으면 현재 작업 중인 SKILL.md를 컨텍스트에서 판단하거나, 최근 수정된 SKILL.md를 대상으로 한다.

---

## 검증 체크리스트

### 1. 필수 frontmatter 필드

| 필드 | 필수 여부 | 기준 |
|------|----------|------|
| `name` | 필수 | 스킬 디렉토리명과 일치해야 함 |
| `description` | 필수 | 트리거 예시가 하나 이상 포함되어야 함 |
| `allowed-tools` | 필수 | 실제 사용 도구만 나열되어야 함 |
| `argument-hint` | 인자 받을 경우 필수 | `$ARGUMENTS`를 사용하는 스킬에 없으면 경고 |
| `user-invocable` | Claude-only 스킬에만 | `false`로 명시되어 있는지 |

### 2. 사용자 승인 흐름 ([STOP] 패턴)

- 파일을 **생성·수정·삭제**하는 스킬이라면 반드시 [STOP] 포인트가 있어야 함
- 외부 서비스에 **쓰기 작업** (커밋, PR 생성, 이슈 생성 등)을 하는 스킬도 동일
- [STOP] 없이 바로 실행하는 스킬은 `allowed-tools`에 Write/Edit/Bash가 없어야 함

### 3. allowed-tools 일관성

스킬 본문에서 실제로 사용하는 도구와 frontmatter의 `allowed-tools`가 일치하는지 확인:

| 도구 | 본문 사용 신호 |
|------|--------------|
| `Bash` | 코드 블록에 `bash` 명령 포함 |
| `Read` | "Read", "파일 읽기" 언급 |
| `Glob` | "Glob", "파일 탐색" 언급 |
| `Grep` | "Grep", "검색" 언급 |
| `Write` | "Write", "파일 생성" 언급 |
| `Edit` | "Edit", "파일 수정" 언급 |

### 4. 행동 원칙 섹션

- 스킬 끝에 "행동 원칙" 또는 "원칙" 섹션이 있는지 확인
- 없어도 오류는 아니지만, 복잡한 스킬이라면 권장

---

## 출력 형식

```
## validate-skill 결과: <파일경로>

### ✅ 통과 항목
- (통과한 항목 목록)

### ⚠️ 문제 항목
- 🔴 Critical — <문제 설명> (<위치>)
- 🟡 Warning — <문제 설명>
- 🟢 Suggestion — <개선 제안>

### 📝 총평
(한 줄 요약)
```

문제가 없으면:

```
## validate-skill 결과: <파일경로>
✅ 모든 항목 통과
```

---

## 행동 원칙

- 검증만 수행하고 파일을 직접 수정하지 않는다
- Critical 항목이 있으면 사용자에게 수정을 권고한다
- 판단하기 어려운 항목은 추측하지 않고 해당 항목을 생략한다
