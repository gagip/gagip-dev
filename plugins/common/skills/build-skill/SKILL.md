---
name: build-skill
description: >
  새 스킬을 만들거나 기존 스킬을 반복 개선하는 메타 스킬. 의도 포착 → SKILL.md 초안 →
  결정론적 테스트 케이스 작성 → 러너 실행 → 정성 피드백 → 일반화 재작성의 루프를 돈다.
  테스트는 번들된 Python 러너(`scripts/run_skill_test.py`)가 `claude -p`로 스킬을 격리
  실행하고 `check(ctx)` 코드로 검증한다 — LLM 심판 없이 결정론적으로.
  사용자가 "스킬 만들어줘", "새 스킬 추가", "이 워크플로 스킬로 만들어줘", "스킬 개선해줘",
  "스킬 반복 개선", "SKILL.md 작성", "스킬 테스트 짜줘", "스킬 평가 돌려줘", "build-skill",
  "이 스킬 회귀 테스트", "스킬 초안 잡아줘" 같은 표현을 쓰면 반드시 이 스킬을 사용한다.
  대화에 이미 반복 워크플로가 있고 사용자가 "이거 스킬화하자"고 하면 그 맥락을 추출해 시작한다.
  스킬 구조·progressive disclosure의 상세 레퍼런스가 필요하면 `plugin-dev:skill-development`를
  함께 참고한다. 스킬 "사용량 지표"는 이 스킬이 아니라 `skill-metrics`가 다룬다.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
argument-hint: (선택) 만들거나 개선할 스킬 이름 또는 경로. 생략 시 대화·질문으로 파악
---

# Build Skill

스킬을 **제품처럼 반복 개발**하는 루프를 제공한다.

```
의도 포착 → SKILL.md 초안 → 테스트 케이스 작성 → 러너 실행(+baseline)
   → 결과·출력물을 사람에게 제시 → 정성 피드백 → 일반화하여 재작성 → 반복
```

사용자가 이 루프의 어디에 있는지 파악해 그 지점부터 합류한다. "스킬 만들어줘"면 처음부터,
초안이 이미 있으면 테스트/반복부터. 사용자가 "평가 없이 감으로 가자"고 하면 그렇게 한다.

---

## 1. 의도 포착

먼저 무엇을 만들지 좁힌다. 대화에 이미 워크플로가 있으면(예: "방금 한 거 스킬로") 히스토리에서
추출한다 — 쓴 도구, 단계 순서, 사용자가 교정한 지점, 입출력 형식.

사용자에게 확인할 것:
1. 이 스킬로 Claude가 무엇을 할 수 있어야 하나
2. 언제 발동해야 하나 (어떤 사용자 표현·맥락)
3. 기대 출력 형식은
4. 결정론적으로 검증 가능한 산출물인가 (파일 변환, 커밋, 워크플로 단계 준수 등) →
   테스트 케이스 유용. 주관적 산출물(글 스타일, 디자인)이면 정성 피드백만.

엣지 케이스·입출력·예시 파일·성공 기준·의존성을 먼저 정리한다. 테스트 프롬프트는 그 다음.

---

## 2. 어디에 두나 (폴더 규칙)

```
plugins/<plugin>/skills/<skill-name>/
├── SKILL.md          (필수) frontmatter + 워크플로 본문
├── scripts/          결정론적·반복 작업 코드. Claude가 매번 재작성하지 않도록 번들
├── references/       필요할 때 읽는 문서. 본문에서 링크, 300줄 넘으면 목차 포함
├── assets/           산출물에 들어가는 템플릿·아이콘·폰트
└── evals/            이 스킬용 테스트 케이스 (*.py, 1파일 1케이스)
```

- 플러그인 선택: 언어·플랫폼 무관 워크플로 → `common`, 개발 특화 → `development`, 그 외 기존 관례.
- **Progressive disclosure 3단계** — 이걸 의식하고 분량을 배분한다:
  1. `name` + `description` — 항상 로드 (~100 단어). 트리거의 전부.
  2. `SKILL.md` 본문 — 발동 시 로드 (<500줄 권장).
  3. `scripts/` `references/` `assets/` — 필요할 때만. 스크립트는 로드 없이 실행 가능.
- 본문이 500줄에 근접하면 계층을 하나 더 만들고 "여기부터는 references/X를 읽어라"로 넘긴다.
- 여러 도메인/프레임워크를 지원하면 `references/<변형>.md`로 쪼개고 본문은 선택 로직만 둔다.

---

## 3. SKILL.md 작성

`assets/SKILL.template.md`를 복사해 시작한다. 채울 것:

| 필드 | 하네스 | 내용 |
|---|---|---|
| `name` | 공통 | kebab-case 식별자. 디렉토리명과 일치 |
| `description` | 공통 | **언제 발동 + 무엇을 하는지.** "언제 쓰나" 정보는 전부 여기. 본문에 넣지 않는다 |
| `allowed-tools` | Claude 전용 | (선택) 이 스킬이 쓰는 도구. Codex는 무시 |
| `argument-hint` | Claude 전용 | (선택) 인자 설명. Codex는 무시 |
| `model` | Claude 전용 | (선택) 특정 모델 필요 시. Codex는 무시 |

**Codex 호환** — 이 레포 스킬은 Claude Code와 Codex가 같은 트리를 읽는다:
- `name`·`description`만이 두 하네스 공통이다. 트리거 표현·하는 일·경계를 전부 여기 담는다.
  Codex는 `allowed-tools` 등을 안 보므로, 본문/필드에만 있는 정보는 Codex에서 사라진다.
- Claude 전용 필드는 유지해도 무해하다(Codex가 무시). 다만 스킬 동작이 그 필드에 **의존하면 안 된다**.
- 본문이 Claude 전용 도구(EnterPlanMode, 구조화 질문, 서브에이전트, Skill 호출 등)를 전제하면
  없는 하네스용 폴백을 문장으로 적는다 (예: "계획 모드 도구가 있으면 그 흐름을, 없으면 파일로
  저장하고 대화로 승인"). `draft-plan`의 `references/plan-mode-fallback.md`가 참고 사례.
- 특정 하네스에서 성립 불가한 스킬이면 감지→이유 알림→종료를 본문에 적는다 (`skill-metrics` 패턴).
- **bash·파일 조작만으로 되는 스킬이 가장 잘 이식된다 — 되도록 그렇게 설계한다.**

**description 작성** — Claude는 스킬을 **저발동**(필요한데 안 씀)하는 경향이 있다. 약간 pushy하게:
구체적 트리거 표현을 여러 개 나열하고, "~ 같은 표현을 쓰면 반드시 이 스킬을 사용한다"로 못박는다.
경쟁 스킬과 헷갈릴 지점이 있으면 경계도 적는다 (예: "사용량 지표는 skill-metrics가 다룬다").

**본문 작성 스타일**:
- 명령형으로 쓴다 ("~하라").
- **왜 그렇게 해야 하는지 설명한다.** 오늘날의 모델은 이유를 알면 기계적 지시를 넘어 판단한다.
  `ALWAYS`/`NEVER` 대문자나 빽빽한 MUST 목록이 나오면 옐로 플래그 — 이유를 풀어 쓸 수 있는지 본다.
- **과적합 경계.** 스킬은 수천~수백만 번 다양한 프롬프트에 쓰인다. 특정 예시에만 맞는 규칙을
  쌓지 말고 넓은 의도 카테고리로 일반화한다.
- 초안을 쓰고 → 새 눈으로 다시 읽고 → 고친다.
- 출력 형식이 있으면 정확한 템플릿을 본문에 박는다. 예시는 Input/Output 쌍으로.

구조 레퍼런스가 더 필요하면 `plugin-dev:skill-development`를 읽는다.

---

## 4. 테스트 케이스 작성

결정론적으로 검증 가능한 스킬이면 케이스를 만든다. 현실적인 프롬프트 2~3개 —
실제 사용자가 칠 법한 것. 사용자에게 보여주고 "이 케이스 맞아? 더 추가할까?" 확인한 뒤 실행.

케이스 = `evals/<이름>.py` **파일 하나**:

```python
"""<이름> — 무엇을 검증하는지 한 줄."""

PROMPT = "커밋해줘"
RUNS = 3                          # 선택, 기본 3 (비결정성 흡수)
SCAFFOLD = r"""
git init -q && git config user.email e@e.com && git config user.name E
printf 'a\n' > app.js && git add app.js && git commit -qm "chore: init"
printf 'b\n' > app.js && printf '# notes\n' > NOTES.md
"""                               # 선택, 각 run 전 임시 디렉토리(=cwd)에서 실행
PERMISSION_MODE = "bypassPermissions"   # 선택, 기본값

def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert ctx.re_match(ctx.git_log_subject(), r"^(feat|fix|chore): .+")
    assert ctx.bash_order(r"git\s+add", r"git\s+commit")
    assert not ctx.bash_ran(r"git\s+push")
    assert ctx.git_status_clean()
```

`check(ctx)` 안은 **100% 코드** — LLM 심판 없음. `AssertionError`의 메시지가 실패 사유로 뜬다.
정확한 문자열 대신 **안정적 결과**로 검증한다 (git log 형식, 파일 존재, push 안 함) — Claude
행동이 비결정적이라.

### ctx 헬퍼 (`scripts/_harness.py` 참조)

| 헬퍼 | 용도 |
|---|---|
| `ctx.skill_fired()` / `ctx.skill_invocations()` | 대상 스킬이 Skill 툴로 발동했나 / 호출된 skill 인자 목록 |
| `ctx.tool_used(name, **input_contains)` | 특정 툴이 (특정 입력 포함해) 호출됐나 |
| `ctx.tool_names()` | 호출된 전체 툴 이름 순서 |
| `ctx.bash_cmds` | 실행된 bash 명령 문자열 리스트 |
| `ctx.bash_ran(regex)` | 그 패턴 명령이 실행됐나 |
| `ctx.bash_order(a, b)` | a 패턴이 b 패턴보다 먼저 (한 명령 안이어도 됨) |
| `ctx.sh(cmd)` / `ctx.run(cmd)` | workdir에서 셸 실행 (검증용) |
| `ctx.git_log_subject()` / `ctx.git_status_clean()` | git 단축 |
| `ctx.read(glob)` / `ctx.exists(glob)` | workdir 파일 |
| `ctx.final_text` | Claude 마지막 텍스트 응답 |
| `ctx.re_match(t, p)` / `ctx.re_search(t, p)` | 정규식 (case에서 `import re` 없이) |

### 코드가 잡는 것 / 사람이 잡는 것

| 결정론적 러너 | 정성 피드백 (사람) |
|---|---|
| 형식·순서·툴 발동·파일 상태·push 안 함 | 톤, 내용 적절성, 가독성, 판단 품질 |

---

## 5. 러너 실행

```bash
python3 <이 스킬>/scripts/run_skill_test.py <대상 스킬 디렉토리> [옵션]
python3 <이 스킬>/scripts/run_skill_test.py --all           # 레포 전체 스킬 (CI 주간 실행)
```

| 옵션 | 의미 |
|---|---|
| `--all` | 루트 아래 `SKILL.md` + `evals/*.py`를 가진 스킬을 모두 실행. `--json`은 `{"all_ok", "skills": [...]}` |
| `--case <이름>` | 특정 케이스만 |
| `--baseline` | 스킬 없이 동일 프롬프트도 1회 → "스킬이 차이를 만드나" 대조. 신규 스킬 평가에 권장 |
| `--runs N` | RUNS 덮어씀 (개발 중 `--runs 1`) |
| `--model <id>` | 현재 세션 모델과 맞추려면 지정 |
| `--threshold 0.66` | 통과 판정 비율 (기본 1.0 = 전 run 통과) |
| `--json [경로]` | 전체 결과 JSON (툴 순서·final_text 포함) |
| `--keep-temp` | 임시 디렉토리 보존 (디버깅) |

출력: 케이스별 `pass/total` + 실패 사유, 종료 코드 0/1.

- `<plugin>/skills/<skill>/` 레이아웃이면 `--setting-sources project --plugin-dir <plugin루트>`로
  **워킹트리 파일을 직접** 격리 실행한다 (설치본과 충돌 없음). 단독 스킬 디렉토리면
  `~/.claude/skills/`에 임시 복사 후 정리한다.
- **러너는 `claude` CLI가 필요하다.** 없는 하네스(Codex 등)에서는 케이스의 `PROMPT`를 수동
  실행하고 `check` 항목을 사람이 확인한다. 케이스 파일 자체는 하네스 무관이다.
- 실행 결과 JSON을 `--json`으로 받아 `final_text`와 출력물을 대화에 붙여 사용자에게 보여준다.
  정성 피드백을 요청한다: "이렇게 나왔는데, 톤·내용 괜찮아? 뭘 바꿀까?"

---

## 6. 반복 개선

피드백과 실패 케이스를 받으면:

1. **일반화한다.** 특정 프롬프트에만 맞는 fiddly한 수정·억압적 MUST를 넣지 말고, 넓은 사용자
   의도로 옮긴다. 고집스러운 이슈는 다른 은유·다른 작업 패턴으로 우회해본다 — 싸게 시도 가능.
2. **본문을 가볍게 유지한다.** 값을 못 하는 부분은 뺀다. transcript(최종 출력만 말고)를 읽어
   스킬이 모델에게 헛짓을 시키고 있으면 그 지시를 지운다.
3. **왜를 설명한다.** 사용자 피드백이 짧거나 짜증나 있어도, 그 사람이 왜 그렇게 썼는지 이해해
   그 이해를 지시에 담는다.
4. **반복되는 helper를 번들한다.** 테스트 run의 transcript에서 매번 비슷한 helper 스크립트를
   새로 짜고 있으면 → 한 번 써서 `scripts/`에 넣고 스킬이 그걸 쓰게 한다.

수정 후 러너를 다시 돌리고(baseline 포함), 결과를 다시 사용자에게. 사용자가 만족하거나,
피드백이 전부 비거나, 진전이 없을 때까지 반복.

---

## 7. 마무리

- `plugins/<plugin>/README.md` 스킬 목록에 새 스킬 행 추가.
- 루트 `README.md` 스킬 카운트 갱신.
- `python3 scripts/check_consistency.py` 통과 확인.
- **`release` 스킬**로 버전 범프(Claude+Codex plugin.json 동시) · CHANGELOG · 태그 · push.
  구현 커밋과 릴리스 커밋을 분리한다.
- 케이스를 추가했으면 그걸로 끝이다 — `.github/workflows/skill-tests.yml`가 매주 토요일
  `--all`로 레포 전체를 돌린다. 별도 CI 등록은 불필요하다.

---

## 계승한 원칙 (skill-creator)

- 스킬은 소수 예시로 반복 개발하되, 그 예시에서만 도는 스킬은 무용하다 — 일반화가 핵심.
- 대문자 MUST·경직된 구조는 옐로 플래그. 이유를 설명해 모델이 이해하게 하는 게 더 강력하다.
- description에 트리거 정보 전부, 약간 pushy하게.
- 반복 작업이 보이면 스크립트로 번들.
