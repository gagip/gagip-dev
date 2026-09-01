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


def load_case(case_path: Path) -> Case:
    """evals/<name>.py 모듈을 로드한다.

    모듈은 최소 PROMPT(str)와 check(ctx) 함수를 정의해야 한다.
    RUNS(int, 기본 3), SCAFFOLD(str, 기본 ""), PERMISSION_MODE(str, 기본 bypassPermissions)는 선택.
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

    return Case(
        name=case_path.stem,
        path=case_path,
        prompt=mod.PROMPT,
        runs=int(getattr(mod, "RUNS", 3)),
        scaffold=str(getattr(mod, "SCAFFOLD", "")),
        permission_mode=str(getattr(mod, "PERMISSION_MODE", "bypassPermissions")),
        check=mod.check,
    )


def discover_cases(skill_dir: Path) -> list[Path]:
    evals = skill_dir / "evals"
    if not evals.is_dir():
        return []
    return sorted(p for p in evals.glob("*.py") if not p.name.startswith("_"))


# --------------------------------------------------------------------------
# 스킬 로드 전략
# --------------------------------------------------------------------------

def read_skill_name(skill_md: Path) -> str:
    m = re.search(r"(?m)^name:\s*(.+?)\s*$", skill_md.read_text())
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
            md.write_text(re.sub(r"(?m)^name:\s*.+$", f"name: {name}", md.read_text(), count=1))
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
            args = ["--setting-sources", "project"]
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
               model: str | None, max_turns: int, timeout: int) -> list[dict]:
    """claude -p를 workdir에서 실행하고 stream-json 이벤트 리스트를 반환한다."""
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

    # CLAUDECODE를 지워 Claude Code 세션 안에서 claude -p 중첩 실행을 허용한다
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    proc = subprocess.run(
        cmd, cwd=workdir, env=env,
        capture_output=True, text=True, timeout=timeout,
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
        return subprocess.run(cmd, cwd=self.workdir, shell=shell, capture_output=True, text=True, **kw)

    run = sh  # 별칭

    def git_log_subject(self, ref: str = "HEAD") -> str:
        return self.sh(["git", "log", "-1", "--format=%s", ref]).stdout.strip()

    def git_status_clean(self) -> bool:
        return self.sh(["git", "status", "--porcelain"]).stdout.strip() == ""

    def read(self, glob: str) -> str:
        """workdir 안에서 glob에 처음 맞는 파일 내용. 없으면 빈 문자열."""
        for p in sorted(self.workdir.glob(glob)):
            if p.is_file():
                return p.read_text()
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


@dataclass
class CaseResult:
    case: str
    runs: list[RunResult]
    baseline: list[RunResult] = field(default_factory=list)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.runs if r.passed)

    @property
    def baseline_pass_count(self) -> int:
        return sum(1 for r in self.baseline if r.passed)

    def ok(self, threshold: float = 1.0) -> bool:
        return bool(self.runs) and (self.pass_count / len(self.runs)) >= threshold


def _one_run(case: Case, loader: SkillLoader, *, with_skill: bool, model: str | None,
             max_turns: int, timeout: int, keep_temp: bool) -> RunResult:
    tmp = Path(tempfile.mkdtemp(prefix=f"buildskill-{case.name}-"))
    try:
        if case.scaffold.strip():
            sc = subprocess.run(["bash", "-c", case.scaffold], cwd=tmp,
                                capture_output=True, text=True)
            if sc.returncode != 0:
                return RunResult(False, f"scaffold 실패: {sc.stderr[:300]}", error=True)

        try:
            events = run_claude(
                case.prompt, tmp,
                extra_args=loader.claude_args(with_skill=with_skill),
                permission_mode=case.permission_mode, model=model,
                max_turns=max_turns, timeout=timeout,
            )
        except (subprocess.TimeoutExpired, RuntimeError) as e:
            return RunResult(False, f"claude 실행 실패: {str(e)[:300]}", error=True)

        ctx = Ctx.build(tmp, events, loader)
        try:
            case.check(ctx)
        except AssertionError as e:
            return RunResult(False, f"check 실패: {e or '(사유 미기재 assert)'}",
                             tool_names=ctx.tool_names(), final_text=ctx.final_text)
        except Exception as e:  # noqa: BLE001 — check 코드 버그도 결과로 노출
            return RunResult(False, f"check 예외: {type(e).__name__}: {e}",
                             error=True, tool_names=ctx.tool_names())
        return RunResult(True, tool_names=ctx.tool_names(), final_text=ctx.final_text)
    finally:
        if keep_temp:
            print(f"  [keep-temp] {tmp}", file=sys.stderr)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


def run_case(skill_dir: Path, case: Case, *, baseline: bool, model: str | None,
             max_turns: int, timeout: int, keep_temp: bool) -> CaseResult:
    with SkillLoader(skill_dir) as loader:
        runs = [
            _one_run(case, loader, with_skill=True, model=model, max_turns=max_turns,
                     timeout=timeout, keep_temp=keep_temp)
            for _ in range(case.runs)
        ]
        base: list[RunResult] = []
        if baseline:
            base = [
                _one_run(case, loader, with_skill=False, model=model, max_turns=max_turns,
                         timeout=timeout, keep_temp=keep_temp)
            ]
    return CaseResult(case=case.name, runs=runs, baseline=base)
