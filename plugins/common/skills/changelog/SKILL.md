---
name: changelog
description: >
  Git 커밋 이력을 분석하여 CHANGELOG 초안을 작성하는 스킬.
  "체인지로그 써줘", "릴리즈 노트 만들어줘", "변경 이력 정리해줘", "changelog 업데이트해줘",
  "버전 정리해줘" 등의 요청이 오면 반드시 이 스킬을 사용할 것.
argument-hint: "[v1.0.0..v2.0.0 또는 태그명 또는 커밋 범위 (선택)]"
allowed-tools: Bash, Read, Write, Edit
---

## 입력

```
$ARGUMENTS
```

---

## 작업 순서

### 1. 범위 결정

`$ARGUMENTS`에 따라 분석 범위를 결정한다.

**`$ARGUMENTS`가 있는 경우**: 입력값을 그대로 범위로 사용
  - 예: `v1.0.0..v2.0.0`, `v1.0.0`, `abc123..HEAD`

**`$ARGUMENTS`가 없는 경우**: 아래 순서로 자동 감지

```bash
# 최근 두 태그 감지
git tag --sort=-version:refname | head -5
```

- 태그가 2개 이상이면 → 최신 태그와 그 이전 태그 사이
- 태그가 1개이면 → 해당 태그부터 HEAD까지
- 태그가 없으면 → 전체 커밋 이력

감지한 범위를 사용자에게 명시한 뒤 진행한다.

---

### 2. 커밋 이력 수집

```bash
git log <범위> --pretty=format:"%H|%s|%b" --no-merges
```

커밋 type 분류 기준 (`commit-guidelines.md` 기준):

| type | 섹션 |
|------|------|
| `feat` | ✨ New Features |
| `fix` | 🐛 Bug Fixes |
| `refactor` | ♻️ Refactoring |
| `style` | 💄 Style |
| `test` | 🧪 Tests |
| `docs` | 📝 Documentation |
| `chore` | 🔧 Chores |
| `ai` | 🤖 AI / Prompts |
| 분류 불가 | 📌 Other |

type 접두사가 없는 커밋은 내용으로 판단하거나 `Other`로 분류한다.

---

### 3. CHANGELOG 초안 작성 후 대기 [STOP]

아래 형식으로 초안을 작성하고 사용자에게 출력한 뒤 **반드시 여기서 멈출 것**.

```markdown
## [버전 또는 날짜] — YYYY-MM-DD

### ✨ New Features
- feat 커밋 요약 ([`abc1234`])

### 🐛 Bug Fixes
- fix 커밋 요약 ([`def5678`])

### ♻️ Refactoring
- ...

### 📝 Documentation
- ...

### 🔧 Chores
- ...
```

규칙:
- 내용 없는 섹션은 생략
- 커밋 메시지 그대로 복사 금지 — 사용자가 읽기 쉬운 문장으로 재작성
- 커밋 해시 7자리를 항목 끝에 표기
- 수정 요청이 오면 초안을 수정한 뒤 다시 대기
- 사용자가 명시적으로 저장을 지시하기 전까지 4단계 실행 금지

---

### 4. 파일 저장 [사용자 승인 후에만 실행]

저장 경로: 프로젝트 루트의 `CHANGELOG.md`

#### CHANGELOG.md가 없는 경우

새로 생성:

```markdown
# CHANGELOG

<초안 내용>
```

#### CHANGELOG.md가 있는 경우

기존 파일을 Read한 뒤, 가장 최신 항목 위에 초안을 삽입.

---

### 5. 완료 알림

```
완료: CHANGELOG.md 업데이트
범위: <분석한 커밋 범위>
항목 수: <총 N개>
```

---

## 행동 원칙

- 커밋 범위를 명시적으로 사용자에게 보여주고 진행
- 파일 저장 전 반드시 사용자 승인 대기
- CHANGELOG.md가 있으면 반드시 Read 후 수정
- 커밋 메시지를 그대로 옮기지 말고 가독성 있게 재작성
