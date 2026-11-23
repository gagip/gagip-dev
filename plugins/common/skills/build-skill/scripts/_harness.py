"""build-skill 테스트 러너의 실행·파싱 로직.

`claude -p`로 스킬을 격리 실행하고, stream-json 이벤트를 파싱해
결정론적 검증에 쓸 `Ctx` 객체를 만든다.

CLI 진입점은 run_skill_test.py. 이 모듈은 로직만 담아 수정 지점을 한 곳에 모은다.
`claude -p`의 출력 포맷이 바뀌면 여기 `Ctx.build`만, 격리 방식이 바뀌면 `claude_args`만 고치면 된다.

격리 전략
---------
스킬을 `<plugin>/skills/<skill>/` 레이아웃(이 레포)에서 쓰면:
  claude -p --setting-sources project --plugin-dir <plugin루트>
로 실행한다. 임시 디렉토리(= cwd)에는 .claude가 없으므로 `--setting-sources project`가
사용자 설정(설치된 마켓플레이스 플러그인 목록 포함)을 통째로 배제하고, `--plugin-dir`로
지정한 워킹트리 플러그인만 로드된다 → 설치본과 이름 충돌 없음, 워킹트리 파일을 직접 검증.

그 외 레이아웃(단독 스킬 디렉토리)이면 `~/.claude/skills/<임시이름>/`에 복사해 로드한다.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path


# --------------------------------------------------------------------------
# 케이스 로딩
# --------------------------------------------------------------------------

@dataclass
class Case:
    name: str
    path: Path
    prompt: str
    runs: int
    scaffold: str
    permission_mode: str
    check: "callable"
    models: list[str] | None = None   # None이면 모든 모델에서 실행
    followups: list[str] = field(default_factory=list)   # 첫 응답 뒤 같은 세션에 차례로 보낼 사용자 답
    grader: str = "code"   # "llm"이면 구조 검사를 통과한 run을 루브릭으로 채점한다(판정은 REVIEW까지)
    review_focus: str = ""   # 사람이 REVIEW 결과에서 볼 것 한 줄
    soft_max_turns: int | None = None    # run 평균 턴이 이보다 크면 REVIEW
    soft_max_tokens: int | None = None   # run 평균 입출력 토큰 합이 이보다 크면 REVIEW


GRADERS = ("code", "llm")


def load_case(case_path: Path) -> Case:
    """evals/<name>.py 모듈을 로드한다.

    모듈은 최소 PROMPT(str)와 check(ctx) 함수를 정의해야 한다.
    RUNS(int, 기본 3), SCAFFOLD(str, 기본 ""), PERMISSION_MODE(str, 기본 bypassPermissions),
    MODELS(list[str], 기본 모든 모델: 이 케이스가 대상으로 삼는 모델만 적는다),
    FOLLOWUPS(list[str], 기본 없음: 질문에 답하는 다음 턴들),
    GRADER("code" | "llm", 기본 "code"), REVIEW_FOCUS(str), SOFT_MAX_TURNS(int), SOFT_MAX_TOKENS(int)는 선택.
    """
    spec = importlib.util.spec_from_file_location(f"buildskill_case_{case_path.stem}", case_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"케이스 모듈을 로드할 수 없음: {case_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if not hasattr(mod, "PROMPT") or not isinstance(mod.PROMPT, str):
        raise ValueError(f"{case_path.name}: PROMPT(str) 상수가 필요하다")
    if not hasattr(mod, "check") or not callable(mod.check):
        raise ValueError(f"{case_path.name}: check(ctx) 함수가 필요하다")

    grader = str(getattr(mod, "GRADER", "code"))
    if grader not in GRADERS:
        raise ValueError(f"{case_path.name}: GRADER는 {GRADERS} 중 하나여야 한다 — {grader!r}")

    return Case(
        name=case_path.stem,
        path=case_path,
        prompt=mod.PROMPT,
        runs=int(getattr(mod, "RUNS", 3)),
        scaffold=str(getattr(mod, "SCAFFOLD", "")),
        permission_mode=str(getattr(mod, "PERMISSION_MODE", "bypassPermissions")),
        check=mod.check,
        models=[str(m) for m in mod.MODELS] if getattr(mod, "MODELS", None) else None,
        followups=[str(f) for f in getattr(mod, "FOLLOWUPS", [])],
        grader=grader,
        review_focus=str(getattr(mod, "REVIEW_FOCUS", "")),
        soft_max_turns=_optional_int(mod, "SOFT_MAX_TURNS"),
        soft_max_tokens=_optional_int(mod, "SOFT_MAX_TOKENS"),
    )


def _optional_int(mod, name: str) -> int | None:
    value = getattr(mod, name, None)
    return None if value is None else int(value)


def discover_cases(skill_dir: Path) -> list[Path]:
    evals = skill_dir / "evals"
    if not evals.is_dir():
        return []
    return sorted(p for p in evals.glob("*.py") if not p.name.startswith("_"))


def discover_skills(root: Path) -> list[Path]:
    """root 아래에서 SKILL.md와 실행 가능한 evals/*.py를 함께 가진 스킬 디렉터리 목록.

    .git 등 숨김 디렉터리는 건너뛴다.
    """
    out: list[Path] = []
    for skill_md in root.rglob("SKILL.md"):
        if any(part.startswith(".") for part in skill_md.relative_to(root).parts):
            continue
        skill_dir = skill_md.parent
        if discover_cases(skill_dir):
            out.append(skill_dir)
    return sorted(out)


def applies_to_model(case: Case, model: str | None) -> bool:
    """케이스가 이 모델을 대상으로 하는가. 모델을 지정하지 않았거나 MODELS가 없으면 항상 True."""
    return model is None or not case.models or model in case.models


# --------------------------------------------------------------------------
# 스킬 로드 전략
# --------------------------------------------------------------------------

def read_skill_name(skill_md: Path) -> str:
    m = re.search(r"(?m)^name:\s*(.+?)\s*$", skill_md.read_text(encoding="utf-8"))
    if not m:
        raise ValueError(f"SKILL.md frontmatter에 name이 없다: {skill_md}")
    return m.group(1).strip().strip('"').strip("'")


class SkillLoader:
    """테스트 대상 스킬을 claude -p가 로드하도록 준비한다.

    plugin 레이아웃이면 --plugin-dir 인자를 주고, 아니면 ~/.claude/skills에 복사한다.
    with 블록을 벗어나면 복사본을 정리한다(plugin 모드는 정리할 것 없음).
    """

    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir.resolve()
        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.is_file():
            raise ValueError(f"SKILL.md가 없다: {self.skill_dir}")
        self.real_name = read_skill_name(skill_md)

        # <plugin>/skills/<skill>/ 레이아웃인가?
        maybe_plugin = self.skill_dir.parent.parent
        self.plugin_root: Path | None = None
        if (self.skill_dir.parent.name == "skills"
                and (maybe_plugin / ".claude-plugin" / "plugin.json").is_file()):
            self.plugin_root = maybe_plugin

        self._copy_dest: Path | None = None

    def __enter__(self) -> "SkillLoader":
        if self.plugin_root is None:
            name = f"{self.real_name}-t{uuid.uuid4().hex[:8]}"
            self._copy_dest = Path.home() / ".claude" / "skills" / name
            self._copy_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(self.skill_dir, self._copy_dest)
            md = self._copy_dest / "SKILL.md"
            md.write_text(re.sub(r"(?m)^name:\s*.+$", f"name: {name}", md.read_text(encoding="utf-8"), count=1), encoding="utf-8")
            self.load_name = name
        else:
            self.load_name = self.real_name
        return self

    def __exit__(self, *exc):
        if self._copy_dest is not None:
            shutil.rmtree(self._copy_dest, ignore_errors=True)

    def claude_args(self, *, with_skill: bool) -> list[str]:
        """claude -p에 붙일 격리/로드 인자."""
        if self.plugin_root is not None:
            # 임시 cwd에는 .claude가 없음 → project 소스만 읽으면 사용자 설정(설치 플러그인) 배제
            # --strict-mcp-config: 계정 커넥터(아티팩트 게시 등) 없이 실행해 평가가 외부로 나가지 않게 한다
            args = ["--setting-sources", "project", "--strict-mcp-config"]
            if with_skill:
                args += ["--plugin-dir", str(self.plugin_root)]
            return args
        # copy 모드: ~/.claude/skills는 user 설정과 무관하게 로드됨.
        # baseline은 전체 스킬을 끄기 어려우므로 대상 스킬만 없는 상태로 근사.
        if with_skill:
            return []
        return ["--disable-slash-commands"]

    def skill_name_matches(self, invoked: str) -> bool:
        """claude가 부른 Skill 인자가 이 스킬인지 (plugin:skill / skill / 임시이름 모두 허용)."""
        target = self.load_name
        return invoked == target or invoked.split(":")[-1] == target.split(":")[-1]


# --------------------------------------------------------------------------
# claude -p 실행
# --------------------------------------------------------------------------

def run_claude(prompt: str, workdir: Path, *, extra_args: list[str], permission_mode: str,
               model: str | None, max_turns: int, timeout: int,
               resume: str | None = None) -> list[dict]:
    """claude -p를 workdir에서 실행하고 stream-json 이벤트 리스트를 반환한다. resume이면 그 세션을 잇는다."""
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--permission-mode", permission_mode,
        "--max-turns", str(max_turns),
        *extra_args,
    ]
    if model:
        cmd += ["--model", model]
    if resume:
        cmd += ["--resume", resume]

    # CLAUDECODE를 지워 Claude Code 세션 안에서 claude -p 중첩 실행을 허용한다
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    proc = subprocess.run(
        cmd, cwd=workdir, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
    )
    events: list[dict] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not events:
        raise RuntimeError(
            f"claude -p가 이벤트를 내지 않았다 (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr[:500]}"
        )
    # 합성 오류(인증 실패 등) 감지
    for e in events:
        if e.get("type") == "result" and e.get("is_error"):
            has_turns = any(ev.get("type") == "assistant"
                            and ev.get("message", {}).get("model") not in (None, "<synthetic>")
                            for ev in events)
            if not has_turns:
                raise RuntimeError(
                    f"claude -p가 API 호출 없이 실패했다 (인증·설정 문제 가능).\n"
                    f"stderr: {proc.stderr[:500]}"
                )
    return events


@dataclass
class RunCost:
    """claude -p 호출 비용. result 이벤트 값의 합이다."""
    duration_ms: int = 0
    input_tokens: int = 0    # usage.input_tokens 그대로(캐시 제외)
    cache_tokens: int = 0    # 캐시 생성 + 캐시 읽기
    output_tokens: int = 0
    turns: int = 0
    usd: float = 0.0

    @property
    def tokens(self) -> int:
        """SOFT_MAX_TOKENS와 비교하는 값: 캐시를 포함한 입출력 전체."""
        return self.input_tokens + self.cache_tokens + self.output_tokens

    def __add__(self, other: "RunCost") -> "RunCost":
        return RunCost(self.duration_ms + other.duration_ms, self.input_tokens + other.input_tokens,
                       self.cache_tokens + other.cache_tokens, self.output_tokens + other.output_tokens,
                       self.turns + other.turns, self.usd + other.usd)


def sum_costs(costs) -> RunCost | None:
    """None(비용 모름)을 뺀 합. 하나도 없으면 None."""
    known = [c for c in costs if c is not None]
    return sum(known, RunCost()) if known else None


def cost_from_events(events: list[dict]) -> RunCost | None:
    """result 이벤트를 모두 더한다. 후속 턴마다 result가 하나씩 생기므로 마지막 것만 읽으면 적게 잡힌다.

    result 이벤트가 하나도 없으면 None(비용을 모름)이다.
    """
    results = [e for e in events if e.get("type") == "result"]
    if not results:
        return None
    total = RunCost()
    for e in results:
        usage = e.get("usage") or {}
        total += RunCost(
            duration_ms=int(e.get("duration_ms") or 0),
            input_tokens=int(usage.get("input_tokens") or 0),
            cache_tokens=int(usage.get("cache_creation_input_tokens") or 0)
            + int(usage.get("cache_read_input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            turns=int(e.get("num_turns") or 0),
            usd=float(e.get("total_cost_usd") or 0.0),
        )
    return total


def session_id(events: list[dict]) -> str | None:
    """마지막 이벤트부터 찾아 세션 ID를 돌려준다(이어 보낸 턴은 새 ID를 받을 수 있다)."""
    return next((e["session_id"] for e in reversed(events) if e.get("session_id")), None)


# --------------------------------------------------------------------------
# Ctx — check(ctx)에 넘어가는 결정론적 헬퍼
# --------------------------------------------------------------------------

@dataclass
class Ctx:
    workdir: Path
    events: list[dict]
    _loader: SkillLoader
    tool_calls: list[dict] = field(default_factory=list)   # [{"name": str, "input": dict}]
    bash_cmds: list[str] = field(default_factory=list)
    final_text: str = ""

    @classmethod
    def build(cls, workdir: Path, events: list[dict], loader: SkillLoader) -> "Ctx":
        tool_calls: list[dict] = []
        texts: list[str] = []
        for e in events:
            if e.get("type") != "assistant":
                continue
            for c in e.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    tool_calls.append({"name": c.get("name", ""), "input": c.get("input", {}) or {}})
                elif c.get("type") == "text":
                    texts.append(c.get("text", ""))
        bash = [tc["input"].get("command", "") for tc in tool_calls if tc["name"] == "Bash"]
        return cls(
            workdir=workdir, events=events, _loader=loader,
            tool_calls=tool_calls, bash_cmds=[b for b in bash if b],
            final_text=texts[-1] if texts else "",
        )

    # --- 툴 호출 ---------------------------------------------------------

    def tool_used(self, name: str, **input_contains) -> bool:
        """name 툴이 호출됐는지. input_contains를 주면 그 키의 값에 문자열이 포함되는지도 확인."""
        for tc in self.tool_calls:
            if tc["name"] != name:
                continue
            if all(str(v) in str(tc["input"].get(k, "")) for k, v in input_contains.items()):
                return True
        return False

    def skill_fired(self) -> bool:
        """테스트 대상 스킬이 Skill 툴로 발동됐는지."""
        return any(self._loader.skill_name_matches(s) for s in self.skill_invocations())

    def skill_invocations(self) -> list[str]:
        """호출된 Skill 툴의 skill 인자 목록 (디버깅용)."""
        return [tc["input"].get("skill", "") for tc in self.tool_calls if tc["name"] == "Skill"]

    def tool_names(self) -> list[str]:
        return [tc["name"] for tc in self.tool_calls]

    def files_read(self, pattern: str | None = None) -> list[str]:
        """Read 툴로 연 파일 경로 목록(슬래시로 통일, 중복 제거). pattern(정규식)을 주면 맞는 것만.

        번들 파일(references/, assets/)을 Claude가 실제로 열었는지 볼 때 쓴다:
        `assert ctx.files_read(r"references/rubric\\.md$")`
        """
        seen: dict[str, None] = {}
        for tc in self.tool_calls:
            if tc["name"] != "Read":
                continue
            path = str(tc["input"].get("file_path", "")).replace("\\", "/")
            if path and (pattern is None or re.search(pattern, path)):
                seen.setdefault(path)
        return list(seen)

    # --- bash ----------------------------------------------------------

    def bash_ran(self, pattern: str) -> bool:
        rx = re.compile(pattern)
        return any(rx.search(c) for c in self.bash_cmds)

    def bash_order(self, first: str, second: str) -> bool:
        """first 패턴이 second 패턴보다 먼저 실행됐는지. 둘 다 있어야 True.

        `git add -A && git commit`처럼 한 명령 안에 둘 다 있으면 문자 위치로 비교한다.
        """
        rx1, rx2 = re.compile(first), re.compile(second)
        joined = "\n\x00\n".join(self.bash_cmds)  # 명령 경계를 유지한 채 하나로
        m1, m2 = rx1.search(joined), rx2.search(joined)
        return m1 is not None and m2 is not None and m1.start() < m2.start()

    # --- 파일시스템 / git ---------------------------------------------

    def sh(self, cmd, **kw) -> subprocess.CompletedProcess:
        """workdir에서 셸 명령 실행 (검증용 — git log 확인 등)."""
        shell = isinstance(cmd, str)
        return subprocess.run(cmd, cwd=self.workdir, shell=shell, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", **kw)

    run = sh  # 별칭

    def git_log_subject(self, ref: str = "HEAD") -> str:
        return self.sh(["git", "log", "-1", "--format=%s", ref]).stdout.strip()

    def git_status_clean(self) -> bool:
        return self.sh(["git", "status", "--porcelain"]).stdout.strip() == ""

    def read(self, glob: str) -> str:
        """workdir 안에서 glob에 처음 맞는 파일 내용. 없으면 빈 문자열."""
        for p in sorted(self.workdir.glob(glob)):
            if p.is_file():
                return p.read_text(encoding="utf-8")
        return ""

    def exists(self, glob: str) -> bool:
        return any(p.is_file() for p in self.workdir.glob(glob))

    # --- 정규식 편의 (case 파일에서 import re 없이) ------------------

    @staticmethod
    def re_match(text: str, pattern: str) -> bool:
        return re.match(pattern, text or "") is not None

    @staticmethod
    def re_search(text: str, pattern: str) -> bool:
        return re.search(pattern, text or "") is not None


# --------------------------------------------------------------------------
# 케이스 실행
# --------------------------------------------------------------------------

@dataclass
class RunResult:
    passed: bool
    reason: str = ""
    error: bool = False       # check 이전 단계 실패 (scaffold, claude 실행)
    tool_names: list[str] = field(default_factory=list)
    final_text: str = ""
    files_read: list[str] = field(default_factory=list)   # Read 툴로 연 파일
    bash_cmds: list[str] = field(default_factory=list)    # 실행한 bash 명령
    skill_fired: bool = False
    cost: RunCost | None = None   # None: 이벤트가 없어 모름(시간 초과 등)
    workdir: Path | None = None   # 판정 뒤 산출물을 복사하고 지울 임시 디렉터리
    snapshot: dict[str, str] = field(default_factory=dict)   # scaffold 직후 {상대 경로: sha1}

    def changed_files(self) -> list[str]:
        """scaffold 이후 새로 생기거나 내용이 바뀐 파일의 상대 경로."""
        if self.workdir is None or not self.workdir.is_dir():
            return []
        now = snapshot_files(self.workdir)
        return sorted(rel for rel, digest in now.items() if self.snapshot.get(rel) != digest)

    def discard(self) -> None:
        if self.workdir is not None:
            shutil.rmtree(self.workdir, ignore_errors=True)
            self.workdir = None


def snapshot_files(root: Path) -> dict[str, str]:
    """root 아래 파일의 {상대 경로: sha1}. .git 아래는 뺀다."""
    out: dict[str, str] = {}
    for f in root.rglob("*"):
        rel = f.relative_to(root)
        if rel.parts[0] == ".git" or not f.is_file():
            continue
        out[rel.as_posix()] = hashlib.sha1(f.read_bytes()).hexdigest()
    return out


@dataclass
class CaseResult:
    case: str
    runs: list[RunResult]
    baseline: list[RunResult] = field(default_factory=list)
    model: str | None = None

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.runs if r.passed)

    @property
    def baseline_pass_count(self) -> int:
        return sum(1 for r in self.baseline if r.passed)

    def discard(self) -> None:
        for r in [*self.runs, *self.baseline]:
            r.discard()


# 결정: run의 임시 디렉터리는 케이스 판정이 끝날 때까지 남긴다. REVIEW·FAIL은 케이스 단위로만 정해지고,
#   LLM 채점도 산출물이 있어야 하므로 run이 끝나자마자 지우면 둘 다 할 수 없다. 지우는 쪽은 호출자
#   (CaseResult.discard)다.
def _one_run(case: Case, loader: SkillLoader, *, with_skill: bool, model: str | None,
             max_turns: int, timeout: int, keep_temp: bool) -> RunResult:
    tmp = Path(tempfile.mkdtemp(prefix=f"buildskill-{case.name}-"))
    snapshot: dict[str, str] = {}
    try:
        result = _run_in(tmp, snapshot, case, loader, with_skill=with_skill, model=model,
                         max_turns=max_turns, timeout=timeout)
    except BaseException:
        # RunResult가 없으면 호출자가 지울 수 없으므로 여기서 지운다
        if not keep_temp:
            shutil.rmtree(tmp, ignore_errors=True)
        raise
    result.workdir, result.snapshot = tmp, snapshot
    if keep_temp:
        print(f"  [keep-temp] {tmp}", file=sys.stderr)
    return result


def _run_in(tmp: Path, snapshot: dict[str, str], case: Case, loader: SkillLoader, *, with_skill: bool,
            model: str | None, max_turns: int, timeout: int) -> RunResult:
    """tmp에서 scaffold → claude -p → check를 돌린다. scaffold 직후 파일 목록을 snapshot에 채운다."""
    if case.scaffold.strip():
        sc = subprocess.run([shutil.which("bash") or "bash", "-c", case.scaffold], cwd=tmp,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if sc.returncode != 0:
            return RunResult(False, f"scaffold 실패: {sc.stderr[:300]}", error=True)
    snapshot.update(snapshot_files(tmp))

    try:
        events = run_claude(
            case.prompt, tmp,
            extra_args=loader.claude_args(with_skill=with_skill),
            permission_mode=case.permission_mode, model=model,
            max_turns=max_turns, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return RunResult(False, f"claude 실행 실패: 시간 초과 {timeout}초 (--timeout으로 늘린다)", error=True)
    except RuntimeError as e:
        return RunResult(False, f"claude 실행 실패: {str(e)[:300]}", error=True)

    for reply in case.followups:
        session = session_id(events)
        assert session, "이어 보낼 세션 ID가 이벤트에 없다"
        try:
            events += run_claude(
                reply, tmp,
                extra_args=loader.claude_args(with_skill=with_skill),
                permission_mode=case.permission_mode, model=model,
                max_turns=max_turns, timeout=timeout, resume=session,
            )
        except subprocess.TimeoutExpired:
            return RunResult(False, f"claude 실행 실패: 후속 턴 시간 초과 {timeout}초", error=True,
                             cost=cost_from_events(events))
        except RuntimeError as e:
            return RunResult(False, f"claude 실행 실패(후속 턴): {str(e)[:300]}", error=True,
                             cost=cost_from_events(events))

    ctx = Ctx.build(tmp, events, loader)
    trace = dict(tool_names=ctx.tool_names(), files_read=ctx.files_read(),
                 bash_cmds=list(ctx.bash_cmds), skill_fired=ctx.skill_fired(),
                 cost=cost_from_events(events))
    try:
        case.check(ctx)
    except AssertionError as e:
        return RunResult(False, f"check 실패: {e or '(사유 미기재 assert)'}",
                         final_text=ctx.final_text, **trace)
    except Exception as e:  # noqa: BLE001 — check 코드 버그도 결과로 노출
        return RunResult(False, f"check 예외: {type(e).__name__}: {e}",
                         error=True, **trace)
    return RunResult(True, final_text=ctx.final_text, **trace)


def run_case(skill_dir: Path, case: Case, *, baseline: bool, model: str | None,
             max_turns: int, timeout: int, keep_temp: bool) -> CaseResult:
    result = CaseResult(case=case.name, runs=[], baseline=[], model=model)
    try:
        with SkillLoader(skill_dir) as loader:
            for _ in range(case.runs):
                result.runs.append(_one_run(case, loader, with_skill=True, model=model, max_turns=max_turns,
                                            timeout=timeout, keep_temp=keep_temp))
            if baseline:
                result.baseline.append(_one_run(case, loader, with_skill=False, model=model,
                                                max_turns=max_turns, timeout=timeout, keep_temp=keep_temp))
    except BaseException:
        # 중간에 끊기면 CaseResult가 호출자에게 가지 않으므로 끝난 run의 임시 폴더를 여기서 지운다
        if not keep_temp:
            result.discard()
        raise
    return result


# 번들 파일을 찾는 디렉터리. test_*·_*로 시작하는 파일은 러너·테스트 전용이라 Claude가 열 일이 없어 뺀다
_BUNDLE_DIRS = ("references", "assets", "scripts")
# LLM 채점기가 읽는 루브릭은 스킬 run이 열지 않아도 쓰이는 파일이다
GRADER_RUBRIC = "references/review-rubric.md"


def unused_bundle_files(skill_dir: Path, results: list[CaseResult]) -> list[str]:
    """스킬 번들(references/·assets/·scripts/) 중 어떤 run에서도 쓰이지 않은 파일의 상대 경로.

    '쓰였다'는 Read 툴로 열렸거나, bash 명령에 상대 경로·파일명이 나온 경우다.
    스킬 적용 run만 본다(baseline 제외). 케이스가 그 기능을 건드리지 않아서 안 쓰였을 수도
    있으므로 실패가 아니라 정리 후보를 알리는 참고 정보다.
    """
    reads = [p for cr in results for r in cr.runs for p in r.files_read]
    cmds = [c for cr in results for r in cr.runs for c in r.bash_cmds]
    unused: list[str] = []
    for d in _BUNDLE_DIRS:
        base = skill_dir / d
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*")):
            if not f.is_file() or f.suffix == ".pyc" or "__pycache__" in f.parts:
                continue
            if f.name.startswith(("test_", "_")):
                continue
            rel = f.relative_to(skill_dir).as_posix()
            if rel == GRADER_RUBRIC:
                continue
            if any(p.endswith("/" + rel) or p == rel for p in reads):
                continue
            if any(rel in c.replace("\\", "/") or f.name in c for c in cmds):
                continue
            unused.append(rel)
    return unused
