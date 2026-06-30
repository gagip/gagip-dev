---
name: release
description: >
  플러그인 릴리즈 전 과정을 수행하는 스킬.
  스킬 검증 → 버전 업데이트 → CHANGELOG 작성 → 커밋 → 태그 → push 순으로 진행.
  "릴리즈해줘", "배포해줘", "버전 올려줘", "release 해줘", "publish 해줘",
  "버전 업데이트하고 배포해줘" 등의 표현이 나오면 반드시 이 스킬을 사용할 것.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
argument-hint: "[patch|minor|major|x.y.z] - 버전 유형 (생략 시 커밋 이력으로 자동 판단)"
---

## 작업 순서

### 1. 사전 정보 수집 (자동)

아래 정보를 자동으로 수집한다.

**플러그인 감지** — 변경된 파일 기준으로 자동 감지:

```bash
git diff --name-only HEAD~1..HEAD 2>/dev/null || git diff --name-only --cached
```

- `plugins/<name>/` 파일 변경 → 해당 `<name>` 플러그인 (common·android·tauri·mobile 등 — **디렉터리명이 곧 플러그인명**, 특정 이름을 하드코딩하지 않는다)
- 여러 플러그인 동시 변경 → 각 플러그인 모두 처리
- `plugins/` 외부 파일 변경(루트 `.claude/` 등)은 플러그인 릴리스 대상이 아니므로 무시한다

**버전 유형 판단** — `$ARGUMENTS`에 버전 유형이 없으면 커밋 이력으로 자동 판단:

```bash
git log <마지막 태그>..HEAD --oneline 2>/dev/null || git log --oneline
```

자동 판단 기준:
- `feat!`, `fix!`, `BREAKING CHANGE` 포함 → `major`
- `feat:` 포함 → `minor`
- 그 외 (`fix:`, `chore:`, `docs:` 등) → `patch`

**신규 플러그인 예외** — 해당 플러그인의 기존 태그(`<name>/v*`)가 하나도 없으면 첫 릴리스다. 자동 범프하지 말고 `plugin.json`의 현재 버전을 그대로 첫 릴리스로 쓴다 (`tauri/v0.1.0`·`mobile/v0.1.0` 선례 — 보통 0.1.0). 릴리스 계획에 "신규 플러그인 첫 릴리스 — 범프 없음"임을 명시한다.

**스킬 검증** — 대상 플러그인의 모든 SKILL.md 점검:

```bash
find plugins/<플러그인명>/skills -name "SKILL.md" 2>/dev/null
```

각 SKILL.md에 대해 frontmatter 필수 필드(`name`, `description`, `allowed-tools`, `argument-hint`)와 `allowed-tools` 일치 여부를 점검한다.

Critical 문제가 발견되면 **즉시 중단**하고 사용자에게 보고한다.

---

### 2. 릴리즈 계획 확인 [STOP - 유일한 중단점]

수집한 정보를 바탕으로 릴리즈 계획을 출력하고 **반드시 여기서 멈출 것**:

```
릴리즈 계획
- 플러그인: <플러그인명>
- 현재 버전: <현재 버전>
- 새 버전: <새 버전> (<버전 유형>)
- 스킬 검증: ✅ 통과 (또는 ⚠️ 경고 N개)

마지막 태그 이후 변경사항:
- <커밋 해시> <커밋 메시지>
...

승인하면 버전 업데이트 → CHANGELOG → 커밋 → 태그 → push까지 자동 진행합니다.
버전 유형을 바꾸려면 patch/minor/major 중 하나를 입력하세요.
진행하려면 "ok" 또는 "확인"을 입력하세요.
```

| 유형 | 변경 | 예시 |
|------|------|------|
| `major` | x+1.0.0 | 0.2.1 → 1.0.0 |
| `minor` | x.y+1.0 | 0.2.1 → 0.3.0 |
| `patch` | x.y.z+1 | 0.2.1 → 0.2.2 |
| `x.y.z` | 그대로 사용 | — |

수정 요청이 오면 반영한 뒤 다시 대기한다.
사용자가 명시적으로 진행("ok", "확인", "계속" 등)을 지시하기 전까지 3단계를 실행하지 말 것.

---

### 3. 준비 단계 (승인 후 자동 실행)

사용자가 승인하면 아래 단계를 **중단 없이** 자동 실행한다.

#### 3-1. 버전 업데이트

`plugin.json`을 Read로 읽은 뒤 Edit으로 version 필드를 새 버전으로 수정:

```
plugins/<플러그인명>/.claude-plugin/plugin.json
```

#### 3-2. CHANGELOG 초안 작성

마지막 태그부터 HEAD까지 **구현 커밋** 이력을 분석하여 CHANGELOG 초안을 메모리에 작성한다.

```bash
git tag --sort=-version:refname | head -3
```

태그가 없으면 전체 커밋 이력을 대상으로 한다. 아직 파일에 저장하지 않는다.

**형식은 레포 컨벤션을 따른다** (루트 `CHANGELOG.md`의 기존 항목을 Read로 확인한 뒤 동일 형식으로):
- 헤더: `## [<플러그인명>/<새 버전>] — YYYY-MM-DD`
- 카테고리(해당하는 것만): `### ✨ New Features` / `### 🐛 Bug Fixes` / `### ♻️ Refactoring` (호환성이 깨지면 `### ♻️ Refactoring (Breaking)`)
- 각 bullet **끝에 그 변경을 만든 구현 커밋의 short 해시**를 `([`hash`])`로 단다 — 이번에 만들 릴리즈 커밋이 아니라 **앞선 구현 커밋**을 가리킨다(자기 참조 금지). 구현 커밋과 릴리즈 커밋(버전 범프 + CHANGELOG)의 분리가 레포 규칙이다.

---

### 4. 최종 확인 [STOP]

CHANGELOG 초안과 커밋 메시지를 함께 보여주고 **반드시 여기서 멈출 것**:

```
최종 확인

[CHANGELOG 초안]
## [<플러그인명>/<새 버전>] — YYYY-MM-DD

### ✨ New Features
- ... ([`<구현 커밋 해시>`])

### ♻️ Refactoring
- ... ([`<구현 커밋 해시>`])

[커밋 메시지]
chore(<플러그인명>): 버전 <새 버전> 릴리즈

[Push 대상]
- 브랜치: <현재 브랜치>
- 태그: <플러그인명>/v<새 버전>

수정할 내용이 있으면 알려주세요. 진행하려면 "ok" 또는 "확인"을 입력하세요.
```

수정 요청이 오면 반영한 뒤 다시 대기한다.
사용자가 승인하기 전까지 5단계를 실행하지 말 것.

---

### 5. 최종 실행 (승인 후 연속 진행)

사용자가 승인하면 아래 단계를 **중단 없이 순서대로** 자동 실행한다.

#### 5-1. CHANGELOG 저장

CHANGELOG 초안을 루트 `CHANGELOG.md` **최상단**(기존 최신 항목 위)에 추가한다. 기존 항목과는 `---` 구분선으로 나눈다. `plugins/<플러그인명>/CHANGELOG.md`가 있어도 그건 stale일 수 있으니 건드리지 않고 루트만 갱신한다.

#### 5-2. 커밋 생성

```bash
git add plugins/<플러그인명>/.claude-plugin/plugin.json CHANGELOG.md
git commit -m "chore(<플러그인명>): 버전 <새 버전> 릴리즈"
```

#### 5-3. 태그 생성

태그 이름: `<플러그인명>/v<새 버전>` (예: `common/v0.2.2`, `android/v0.3.0`)

```bash
git tag -a "<플러그인명>/v<새 버전>" -m "Release <플러그인명> v<새 버전>"
```

#### 5-4. Push

push는 **개인 계정 `gagip`**로 한다 (레포 규칙). gh 활성 계정이 `gagip`가 아니면 `gh auth switch --user gagip`로 전환해 push하고, 끝나면 원래 계정으로 복원한다.

```bash
git push origin <현재 브랜치>
git push origin "<플러그인명>/v<새 버전>"
```

---

### 6. 완료 알림

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
- **중단점은 2단계(릴리즈 계획 확인)와 4단계(최종 확인) 두 번뿐**이다. 각 승인 이후엔 다음 중단점까지 자동 진행한다
- `plugin.json` 수정 전 반드시 Read로 현재 내용을 확인한다
- 태그는 `<플러그인명>/v<버전>` 형식을 따른다
- CHANGELOG는 루트 `CHANGELOG.md`의 기존 형식(`## [<플러그인명>/<버전>] — 날짜`, 이모지 카테고리, bullet 끝 구현 커밋 해시 `([`hash`])`)을 그대로 따른다 — 자체 형식을 만들지 않는다
- push는 개인 계정 `gagip`로 한다 (다르면 전환 후 복원)
