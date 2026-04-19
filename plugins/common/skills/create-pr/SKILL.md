---
name: create-pr
description: >
  현재 브랜치의 변경사항을 분석하여 GitHub PR을 생성하거나 기존 PR 본문을 업데이트하는 스킬.
  "PR 만들어줘", "풀리퀘 올려줘", "PR 생성해줘", "pull request 만들어줘",
  "PR 본문 업데이트해줘" 등의 표현이 나오면 반드시 이 스킬을 사용할 것.
allowed-tools: Bash
argument-hint: (선택) PR 제목 또는 추가 지시사항. 생략 시 변경사항을 분석해 자동 생성
---

## 작업 순서

### 1. 변경사항 수집

base 브랜치 감지:
```bash
git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||'
```
감지 실패 시 `main`을 기본값으로 사용.

변경사항 확인 (감지한 base 브랜치로 대체):
```bash
git log <base>..<HEAD> --oneline
git diff <base>...<HEAD> --stat
```

필요시 주요 파일 diff 상세 확인.

### 2. remote push 확인

```bash
git status -sb
```

현재 브랜치가 remote에 없으면 PR 생성 전에 push:
```bash
git push -u origin HEAD
```

### 3. PR 본문 초안 작성 후 대기 [STOP]

아래 템플릿으로 작성:

```markdown
## Summary
<!-- 1-2문장 요약 -->

## Key Changes
<!-- 주요 변경사항 목록 -->
-

## Technical Details
<!-- 구현 방식·아키텍처 변경·핵심 로직 -->

## Rationale
<!-- 이 방식을 선택한 이유·검토한 대안 -->
```

- 개조식으로 작성
- 초안 작성 후 사용자에게 출력하고 **반드시 여기서 멈출 것**
- 수정 요청이 오면 본문을 수정한 뒤 다시 대기할 것
- 사용자가 명시적으로 생성을 지시("올려줘", "생성해줘", "만들어줘" 등)하기 전까지 4단계를 실행하지 말 것
- 스킬 호출 자체를 PR 생성 승인으로 간주하지 말 것

### 4. PR 생성 또는 업데이트 [사용자 승인 후에만 실행]

PR 존재 여부 확인:
```bash
gh pr view --json number,url 2>/dev/null
```

**PR이 없는 경우** — 생성 (기본 draft):
```bash
gh pr create --draft --title "<PR 제목>" --body "$(cat <<'EOF'
<PR 본문>
EOF
)"
```

사용자가 "바로 올려줘", "draft 말고", "ready로" 등 명시적으로 요청한 경우 `--draft` 옵션을 제거한다.

**PR이 이미 있는 경우** — 업데이트:

기존 본문을 먼저 읽어 내용을 보존한다:
```bash
gh pr view --json body --jq '.body'
```

기존 본문을 기반으로 필요한 부분만 수정하여 업데이트:
```bash
gh pr edit --title "<PR 제목>" --body "$(cat <<'EOF'
<PR 본문>
EOF
)"
```

- 기존 본문의 구조와 내용을 최대한 유지하고, 변경된 부분만 반영한다
- draft/ready for review 상태는 변경하지 않는다

- 필요시 `--reviewer`, `--label` 옵션 추가
- 완료 후 PR URL 사용자에게 전달

## 행동 원칙

- 스킬 호출 자체를 PR 생성 승인으로 간주하지 않는다 — 반드시 사용자 명시적 지시 후에만 생성한다
- PR 제목은 `<type>: <요약>` 형식을 따른다 (commit-guidelines.md의 커밋 타입 기준)
- remote push는 PR 생성에 필요한 경우에만 자동으로 수행한다
- PR은 기본적으로 draft로 생성한다 — 사용자가 명시적으로 draft 해제를 요청한 경우에만 일반 PR로 생성한다
- PR 업데이트 시 draft/ready for review 상태는 변경하지 않는다
- PR 본문 업데이트 시 기존 본문을 먼저 읽고 내용을 기반으로 필요한 부분만 수정한다 — 전체를 새로 작성하지 않는다
