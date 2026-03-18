---
name: release
description: >
  플러그인 릴리즈 전 과정을 수행하는 스킬.
  스킬 검증 → 버전 업데이트 → CHANGELOG 작성 → 커밋 → 태그 → push 순으로 진행.
  "릴리즈해줘", "배포해줘", "버전 올려줘", "release 해줘", "publish 해줘",
  "버전 업데이트하고 배포해줘" 등의 표현이 나오면 반드시 이 스킬을 사용할 것.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

## 작업 순서

### 1. 대상 플러그인 결정

`$ARGUMENTS`에서 버전 유형을 파싱한다.

**플러그인명은 항상 변경된 파일을 기준으로 자동 감지한다** (`전체` 포함 어떤 입력이든 동일):

```bash
git diff --name-only HEAD~1..HEAD 2>/dev/null || git diff --name-only --cached
```

- `plugins/common/` 파일 변경 → common 플러그인만 처리
- `plugins/android/` 파일 변경 → android 플러그인만 처리
- 둘 다 변경 → 변경된 두 플러그인 모두 순서대로 처리

**버전 유형이 없는 경우**: 마지막 태그 이후 커밋 이력을 분석하여 자동 판단

```bash
git log <마지막 태그>..HEAD --oneline 2>/dev/null || git log --oneline
```

자동 판단 기준 (초안용):
- `feat!`, `fix!`, `BREAKING CHANGE` 포함 → `major`
- `feat:` 포함 → `minor`
- 그 외 (`fix:`, `chore:`, `docs:` 등) → `patch`

현재 버전 확인:
```bash
cat plugins/<플러그인명>/.claude-plugin/plugin.json
```

자동 판단 후 사용자에게 반드시 확인:

```
마지막 태그 이후 변경사항:
- <커밋 해시> <커밋 메시지>
- <커밋 해시> <커밋 메시지>
...

변경 내용 요약:
- <변경된 파일/스킬명>: <한 줄 설명>
...

커밋 이력을 분석한 결과 <판단 유형>으로 판단했습니다.

버전 유형을 선택해주세요 (엔터 시 <판단 유형> 적용):
1. patch (x.y.z+1)
2. minor (x.y+1.0)
3. major (x+1.0.0)
```

사용자가 다른 유형을 선택하면 해당 유형으로 버전을 계산한다.

---

### 2. 스킬 파일 검증

대상 플러그인의 모든 SKILL.md를 검증한다.

```bash
find plugins/<플러그인명>/skills -name "SKILL.md" 2>/dev/null
```

각 SKILL.md에 대해 `validate-skill` 스킬 기준으로 점검:
- frontmatter 필수 필드 (`name`, `description`, `allowed-tools`, `argument-hint`)
- [STOP] 패턴 — 파일 쓰기/외부 쓰기 스킬에 존재하는지
- `allowed-tools`와 실제 사용 도구 일치 여부

**Critical 문제가 발견되면 여기서 멈추고 사용자에게 보고한다.**
문제가 없거나 Warning/Suggestion만 있으면 다음 단계로 진행한다.

---

### 3. 새 버전 계산 및 확인 [STOP]

현재 버전(`x.y.z`)에서 버전 유형에 따라 계산:

| 유형 | 변경 | 예시 |
|------|------|------|
| `major` | x+1.0.0 | 0.2.1 → 1.0.0 |
| `minor` | x.y+1.0 | 0.2.1 → 0.3.0 |
| `patch` | x.y.z+1 | 0.2.1 → 0.2.2 |
| `x.y.z` | 그대로 사용 | — |

아래 내용을 사용자에게 출력하고 **반드시 여기서 멈출 것**:

```
릴리즈 계획
- 플러그인: <플러그인명>
- 현재 버전: <현재 버전>
- 새 버전: <새 버전>
- 스킬 검증: ✅ 통과 (또는 ⚠️ 경고 N개)

계속하려면 확인해주세요.
```

수정 요청이 오면 반영한 뒤 다시 대기한다.
사용자가 명시적으로 진행("계속", "확인", "ok" 등)을 지시하기 전까지 4단계를 실행하지 말 것.

---

### 4. 버전 업데이트 [사용자 승인 후에만 실행]

`plugin.json`의 version 필드를 새 버전으로 수정:

```
plugins/<플러그인명>/.claude-plugin/plugin.json
```

Edit 도구로 `"version": "<현재 버전>"` → `"version": "<새 버전>"` 으로 변경.

---

### 5. CHANGELOG 작성

`changelog` 스킬을 호출하여 변경 이력을 작성한다.

범위: 마지막 태그부터 HEAD까지

```bash
git tag --sort=-version:refname | head -3
```

태그가 없으면 전체 커밋 이력을 대상으로 한다.

CHANGELOG 초안을 작성하여 사용자에게 보여주고 **[STOP]**한다.
사용자가 승인하면 `CHANGELOG.md`에 저장한다.

---

### 6. 커밋 생성 [STOP]

아래 커밋 메시지 초안을 사용자에게 보여주고 **반드시 여기서 멈출 것**:

```
chore(<플러그인명>): 버전 <새 버전> 릴리즈
```

수정 요청이 오면 반영한 뒤 다시 대기한다.
사용자가 명시적으로 커밋을 지시하기 전까지 커밋을 실행하지 말 것.

**커밋 실행**:
```bash
git add plugins/<플러그인명>/.claude-plugin/plugin.json CHANGELOG.md
git commit -m "chore(<플러그인명>): 버전 <새 버전> 릴리즈"
```

---

### 7. Git 태그 생성 [사용자 승인 후에만 실행]

태그 이름: `<플러그인명>/v<새 버전>`
예: `common/v0.2.2`, `android/v0.3.0`

```bash
git tag -a "<플러그인명>/v<새 버전>" -m "Release <플러그인명> v<새 버전>"
```

---

### 8. Push [STOP]

push 전에 사용자에게 확인:

```
push 대상:
- 브랜치: <현재 브랜치>
- 태그: <플러그인명>/v<새 버전>

push를 진행할까요?
```

사용자가 승인하면:
```bash
git push origin <현재 브랜치>
git push origin "<플러그인명>/v<새 버전>"
```

---

### 9. 완료 알림

```
✅ 릴리즈 완료!

- 플러그인: <플러그인명>
- 버전: <이전 버전> → <새 버전>
- 태그: <플러그인명>/v<새 버전>
- 커밋: <short hash>
```

---

## 행동 원칙

- 스킬 검증에서 Critical 문제가 있으면 즉시 중단하고 사용자에게 보고한다
- 버전 계산, 커밋, 태그, push 각 단계 전 반드시 사용자 확인을 받는다
- `plugin.json` 수정 전 반드시 Read로 현재 내용을 확인한다
- push는 사용자가 명시적으로 승인할 때만 수행한다
- 태그는 `<플러그인명>/v<버전>` 형식을 따른다
