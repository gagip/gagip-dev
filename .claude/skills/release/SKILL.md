---
name: release
description: >
  플러그인 릴리즈 전 과정을 수행하는 스킬.
  스킬 검증 → 버전 업데이트 → CHANGELOG 작성 → 커밋 → 태그 → push 순으로 진행.
  "릴리즈해줘", "배포해줘", "버전 올려줘", "release 해줘", "publish 해줘",
  "버전 업데이트하고 배포해줘" 등의 표현이 나오면 반드시 이 스킬을 사용할 것.
  중간 확인 없이 push까지 한 번에 끝낸다 — 이 스킬을 부르는 것이 곧 push 승인이다.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

## 작업 순서

### 1. 사전 정보 수집 (자동)

**먼저 원격 참조를 갱신한다** — 아래 수집이 전부 `origin/main`·로컬 태그를 기준으로 판단하므로, 참조가 낡아 있으면 릴리스 상태를 잘못 읽는다:

```bash
git fetch origin --tags
```

> 이 단계를 건너뛰면 이미 릴리스·push된 버전이 "미push 커밋"으로 보인다. 실제로 로컬 `origin/main`이 낡아 릴리스 커밋 4개가 미push로 잡히고 "이전 릴리스가 태그 없이 끊겼다"고 오진한 적이 있다 — fetch 후 확인해보니 정상 릴리스 상태였고 실제 미push는 1개뿐이었다.

그다음 아래 정보를 수집한다.

**플러그인 감지** — 변경된 파일 기준으로 자동 감지:

```bash
git diff --name-only HEAD~1..HEAD 2>/dev/null || git diff --name-only --cached
```

- `plugins/<name>/` 파일 변경 → 해당 `<name>` 플러그인 (디렉터리명이 곧 플러그인명, 하드코딩 금지)
- 여러 플러그인 동시 변경 → 각 플러그인 모두 처리
- `plugins/` 외부 파일 변경(루트 `.claude/` 등)은 릴리스 대상이 아니므로 무시한다

**버전 유형 판단** — 호출 인자로 버전 유형을 받지 않았으면 커밋 이력으로 자동 판단:

```bash
git log <마지막 태그>..HEAD --oneline 2>/dev/null || git log --oneline
```

- `feat!`, `fix!`, `BREAKING CHANGE` 포함 → `major`
- `feat:` 포함 → `minor`
- 그 외 (`fix:`, `chore:`, `docs:` 등) → `patch`

| 유형 | 변경 | 예시 |
|------|------|------|
| `major` | x+1.0.0 | 0.2.1 → 1.0.0 |
| `minor` | x.y+1.0 | 0.2.1 → 0.3.0 |
| `patch` | x.y.z+1 | 0.2.1 → 0.2.2 |
| `x.y.z` | 그대로 사용 | — |

호출 인자로 `patch`·`minor`·`major`·`x.y.z`를 받았으면 자동 판단을 무시하고 그것을 쓴다.

**신규 플러그인 예외** — 해당 플러그인의 기존 태그(`<name>/v*`)가 하나도 없으면 첫 릴리스다. 자동 범프하지 말고 `plugin.json`의 현재 버전을 그대로 첫 릴리스로 쓴다. 완료 보고에 "신규 플러그인 첫 릴리스 — 범프 없음"을 명시한다.

**스킬·매니페스트 검증** — 대상 플러그인의 모든 SKILL.md와 공유 메타데이터를 점검:

```bash
find plugins/<플러그인명>/skills -name "SKILL.md" 2>/dev/null
```

각 SKILL.md에 대해 frontmatter 필수 필드(`name`, `description`, `allowed-tools`)와 `allowed-tools` 일치 여부를 점검한다.

```bash
python3 scripts/check_consistency.py
uv run --with pyyaml python /path/to/plugin-creator/scripts/validate_plugin.py plugins/<플러그인명>
```

Codex validator의 실제 경로는 현재 환경에 설치된 `plugin-creator` 스킬에서 확인한다. 두 검사가 모두 통과해야 한다.

**validator를 실행할 수 없는 경우** — `plugin-creator`가 현재 환경에 없어 스크립트 경로를 찾지 못하면, 검사 실패로 취급해 중단하지 않는다. 그대로 진행하되 완료 보고에 `Codex validator: ⚠️ 미실행 (plugin-creator 없음)`을 명시한다. **돌려서 실패한 것과 아예 못 돌린 것은 다르다** — 전자는 즉시 중단이지만, 후자는 `check_consistency.py`가 두 매니페스트의 `name`·`version`·`description` 일치를 이미 확인하므로 매니페스트 구조를 건드리지 않은 변경이면 위험이 낮다.

Critical 문제가 발견되면 **즉시 중단**하고 사용자에게 보고한다.

**CHANGELOG 초안 작성** — 마지막 태그부터 HEAD까지 구현 커밋 이력을 분석해 초안을 메모리에 작성한다.

`plugins/<플러그인명>/CHANGELOG.md`를 Read로 확인해 기존 형식을 그대로 따른다:
- 헤더: `## [<새 버전>] - YYYY-MM-DD` (플러그인명 없이 버전만, 하이픈 `-`)
- 카테고리(해당하는 것만): `### ✨ Feat` / `### 🐛 Fix` / `### ♻️ Refactor` / `### 📝 Docs` — 커밋 type과 같은 축약형
- 각 bullet은 `- **<스킬명>**: ...` 로 시작하고, 끝에 구현 커밋 short 해시를 `` (`hash`) `` 로 단다 — 릴리즈 커밋이 아닌 앞선 구현 커밋을 가리킨다 (자기 참조 금지)
- 항목 사이에 `---` 구분선을 넣지 않는다

> 루트 `CHANGELOG.md`는 `common/0.18.2`까지의 과거 기록이다. **더 이상 갱신하지 않는다** — 0.19.0부터 플러그인별 파일로 옮겼다.

---

### 2. 실행 (중단 없이 연속 진행)

수집이 끝나면 확인을 구하지 않고 아래 단계를 순서대로 실행한다.

#### 2-1. 버전 업데이트

두 `plugin.json`을 Read로 읽은 뒤 Edit으로 version 필드를 같은 새 버전으로 수정:

```
plugins/<플러그인명>/.claude-plugin/plugin.json
plugins/<플러그인명>/.codex-plugin/plugin.json
```

#### 2-2. CHANGELOG 저장

CHANGELOG 초안을 `plugins/<플러그인명>/CHANGELOG.md` **최상단**(기존 최신 항목 위)에 추가한다. 구분선 없이 바로 잇는다. 루트 `CHANGELOG.md`는 건드리지 않는다 — 0.18.2까지의 과거 기록이다.

#### 2-3. 커밋 생성

```bash
git add plugins/<플러그인명>/.claude-plugin/plugin.json plugins/<플러그인명>/.codex-plugin/plugin.json plugins/<플러그인명>/CHANGELOG.md
git commit -m "chore(<플러그인명>): 버전 <새 버전> 릴리즈"
```

#### 2-4. 태그 생성

```bash
git tag -a "<플러그인명>/v<새 버전>" -m "Release <플러그인명> v<새 버전>"
```

#### 2-5. Push

push는 **개인 계정 `gagip`**로 한다. gh 활성 계정이 `gagip`가 아니면 `gh auth switch --user gagip`로 전환 후 push하고, 끝나면 원래 계정으로 복원한다.

```bash
git push origin <현재 브랜치>
git push origin "<플러그인명>/v<새 버전>"
```

---

### 3. 완료 보고

중단점이 없으므로 사용자는 이 보고로 무엇이 나갔는지 처음 확인한다. **무엇을 검증했는지까지 적는다.**

```
✅ 릴리즈 완료!

- 플러그인: <플러그인명>
- 버전: <이전 버전> → <새 버전>
- 태그: <플러그인명>/v<새 버전>
- 커밋: <short hash>
- 검증: check_consistency.py ✅ / Codex validator <✅ 또는 ⚠️ 미실행 (plugin-creator 없음)>
```

되돌리려면 `git reset --hard <이전 커밋>`과 태그 삭제가 필요하고, push 이후면 force-push가 필요하다는 점을 함께 알린다.

---

## 행동 원칙

- 스킬 검증에서 Critical 문제가 있으면 즉시 중단하고 사용자에게 보고한다
- 중단점을 두지 않는다. 1단계 수집이 끝나면 3단계 보고까지 이어서 진행한다 (검증 실패는 예외)
- 두 `plugin.json` 수정 전 반드시 Read로 현재 내용을 확인하고 `name`·`version`·`description`이 일치하는지 검증한다
- Claude와 Codex manifest의 버전은 항상 동일하게 범프한다
- 릴리스 직전 Codex plugin validator와 `python3 scripts/check_consistency.py`를 다시 실행한다
- 태그는 `<플러그인명>/v<버전>` 형식을 따른다
- CHANGELOG는 `plugins/<플러그인명>/CHANGELOG.md`의 기존 형식을 그대로 따른다 — 자체 형식을 만들지 않는다 (루트 `CHANGELOG.md`는 과거 기록이라 갱신 대상이 아니다)
- push는 개인 계정 `gagip`로 한다 (다르면 전환 후 복원)
