"""PR 생성·머지 전에 레포별 필수 검사 기록이 있는지 보는 증거 문턱.

필수 명령은 레포 밖 설정 파일(`EVIDENCE_GATE_CONFIG`, 기본 `~/.claude/evidence-gate.json`)이 정한다:
`{"repos": {"owner/name": {"conditions": {"타입 검사": ["npm", "run", "typecheck"]}}}}`.
기록은 `EVIDENCE_GATE_ROOT`(기본 `~/.claude/evidence`) 아래 레포·브랜치별 폴더에 `verify.py` 형식으로 남는다.
에이전트의 실수를 막는 장치이고, 일부러 우회하는 것까지 막지는 못한다.

  gate.py run --condition <이름>     설정된 명령을 실행해 기록한다(현재 폴더의 레포·브랜치)
  gate.py review --report <파일>     끝 리뷰 보고 파일이 있다는 기록을 남긴다(레포 밖 파일)
  gate.py status                     현재 브랜치의 기록 상태를 보인다
  gate.py hook --harness claude|codex  PreToolUse 훅 입력(stdin)을 판정한다
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

try:
    import verify
except Exception as exc:  # 훅으로 불릴 때 모듈 오류도 통과가 아니라 차단으로 끝나야 한다.
    verify = None
    VERIFY_IMPORT_ERROR = exc

REVIEW = "끝 리뷰"
REVIEW_COMMAND = [sys.executable, "-c",
                  "import pathlib,sys; sys.exit(0 if pathlib.Path(sys.argv[1]).stat().st_size > 0 else 1)"]
DOC_SUFFIXES = (".md", ".mdx", ".rst", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
VALUE_FLAGS = {"-R", "--repo", "-B", "--base", "-H", "--head", "-t", "--title", "-b", "--body", "-F",
               "--body-file", "-l", "--label", "-a", "--assignee", "-r", "--reviewer", "-m", "--milestone",
               "-p", "--project", "-T", "--template", "--subject", "--author-email", "--match-head-commit",
               "-A", "--recover"}
OPERATORS = {"&&", "||", ";", "|", "&", "(", ")", ";;", "|&"}
GH_CALL = re.compile(r"\bgh\s+pr\s+(create|merge)\b")
CD_TARGET = re.compile(r"(?:^|&&|;|\|\||\n)\s*cd\s+(\"[^\"]+\"|'[^']+'|[^\s;&|]+)")


def config_path() -> Path:
    return Path(os.environ.get("EVIDENCE_GATE_CONFIG", "~/.claude/evidence-gate.json")).expanduser()


def evidence_root() -> Path:
    return Path(os.environ.get("EVIDENCE_GATE_ROOT", "~/.claude/evidence")).expanduser()


def load_config() -> dict[str, dict[str, list[str]]]:
    path = config_path()
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    repos = data.get("repos")
    if not isinstance(repos, dict):
        raise ValueError(f"{path}: repos 객체가 필요하다")
    result = {}
    for name, entry in repos.items():
        conditions = entry.get("conditions") if isinstance(entry, dict) else None
        if not isinstance(conditions, dict) or not conditions:
            raise ValueError(f"{path}: {name}에 conditions가 필요하다")
        for condition, command in conditions.items():
            if condition == REVIEW or "사람 확인" in condition:
                raise ValueError(f"{path}: 조건 이름 {condition}은 예약돼 있다")
            if not isinstance(command, list) or not command or not all(isinstance(p, str) for p in command):
                raise ValueError(f"{path}: {name}/{condition} 명령은 문자열 목록이어야 한다")
        result[name.lower()] = conditions
    return result


def normalize_repo(value: str) -> str | None:
    value = value.strip()
    match = re.search(r"github[^:/]*[:/]+([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", value)
    if match:
        return f"{match.group(1)}/{match.group(2)}".lower()
    if re.fullmatch(r"[\w.-]+/[\w.-]+", value):
        return value.lower()
    return None


def run_git(cwd: Path, *args: str) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                              text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def local_repo(cwd: Path) -> tuple[Path, str] | None:
    root = run_git(cwd, "rev-parse", "--show-toplevel")
    origin = run_git(cwd, "remote", "get-url", "origin")
    name = normalize_repo(origin) if origin else None
    if not root or not name:
        return None
    return Path(root), name


def evidence_dir(repo: str, branch: str) -> Path:
    return evidence_root() / repo.replace("/", "__") / hashlib.sha256(branch.encode()).hexdigest()[:16]


def required(conditions: dict[str, list[str]]) -> dict[str, list[str] | None]:
    return {**conditions, REVIEW: None}


def is_doc(path: str) -> bool:
    return path.lower().endswith(DOC_SUFFIXES)


def read_record(directory: Path, condition: str) -> dict:
    item = json.loads((directory / f"{verify.key(condition)}.json").read_text())
    if not isinstance(item, dict):
        raise ValueError("기록은 객체여야 한다")
    return item


def command_matches(item: dict, expected: list[str] | None) -> bool:
    command = item.get("command")
    if expected is None:  # 기록할 때와 판정할 때 파이썬 경로가 다를 수 있다.
        return isinstance(command, list) and len(command) == 4 and command[1:3] == REVIEW_COMMAND[1:3]
    return command == expected


def check_local(root: Path, repo: str, branch: str, conditions: dict[str, list[str]]) -> list[str]:
    directory = evidence_dir(repo, branch)
    names = list(required(conditions))
    failures = verify.check(root, directory, names)
    head = run_git(root, "rev-parse", "HEAD")
    for name, expected in required(conditions).items():
        try:
            item = read_record(directory, name)
        except (OSError, ValueError):
            continue
        if not command_matches(item, expected):
            failures.append(f"검증 조건 {name}: 기록된 명령이 설정과 다름")
        if item.get("head") != head or item.get("dirty") is not False:
            failures.append(f"검증 조건 {name}: 커밋된 현재 HEAD의 깨끗한 작업 트리에서 돌린 기록이 아님")
    return failures


def check_remote(repo: str, branch: str, head: str, conditions: dict[str, list[str]]) -> list[str]:
    directory = evidence_dir(repo, branch)
    failures = []
    for name, expected in required(conditions).items():
        try:
            item = read_record(directory, name)
            if item.get("status") != "passed" or item.get("exit_code") != 0:
                raise ValueError("성공한 실행 기록이 없음")
            if not command_matches(item, expected):
                raise ValueError("기록된 명령이 설정과 다름")
            if item.get("head") != head or item.get("dirty") is not False:
                raise ValueError(f"PR HEAD {head[:12]}의 깨끗한 작업 트리에서 돌린 기록이 아님")
            if item.get("before") != item.get("after"):
                raise ValueError("검증 중 코드가 바뀜")
            log = directory / str(item.get("log", ""))
            if hashlib.sha256(log.read_bytes()).hexdigest() != item.get("log_sha256"):
                raise ValueError("실행 로그가 기록과 다름")
        except (OSError, ValueError, TypeError) as exc:
            failures.append(f"검증 조건 {name}: {exc}")
    return failures


def gh_invocations(command: str) -> list[tuple[str, list[str], str | None]]:
    """명령 문자열의 `gh pr create|merge` 호출과 인자, 그 앞의 `cd` 대상을 찾는다.

    `bash -c`·`eval`의 문자열 안이거나 따옴표가 안 닫혀 해석하지 못하면, 인자를 모르는 호출로 보고 현재 폴더와
    `-R` 값으로 판정한다. 놓치는 쪽보다 묻는 쪽을 고른다.
    """
    if not GH_CALL.search(command):
        return []
    cds = [m.group(1).strip("\"'") for m in CD_TARGET.finditer(command)]
    cd_target = str(Path(*cds)) if cds else None
    try:
        lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        tokens = []
    found = []
    for i, token in enumerate(tokens):
        if Path(token).name == "gh" and tokens[i + 1:i + 2] == ["pr"] and tokens[i + 2:i + 3] in (["create"], ["merge"]):
            end = i + 3
            while end < len(tokens) and tokens[end] not in OPERATORS:
                end += 1
            found.append((tokens[i + 2], tokens[i + 3:end], cd_target))
    nested = any(tokens[i - 1] in ("-c", "eval") and GH_CALL.search(t) for i, t in enumerate(tokens) if i > 0)
    if not found and (not tokens or nested):
        for match in GH_CALL.finditer(command):
            rest = command[match.end():].split("\n", 1)[0]
            repo = re.search(r"(?:-R|--repo)[=\s]*([\w.-]+/[\w.-]+)", rest)
            found.append((match.group(1), ["-R", repo.group(1)] if repo else [], cd_target))
    return found


def option(args: list[str], *names: str) -> str | None:
    for index, arg in enumerate(args):
        for name in names:
            if arg == name and index + 1 < len(args):
                return args[index + 1]
            if len(name) == 2 and arg.startswith(name) and len(arg) > 2:
                return arg[2:]
            if name.startswith("--") and arg.startswith(name + "="):
                return arg.split("=", 1)[1]
    return None


def positional(args: list[str]) -> str | None:
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg in VALUE_FLAGS:
            skip = True
            continue
        if not arg.startswith("-"):
            return arg
    return None


def judge_create(args: list[str], cwd: Path, config: dict) -> str | None:
    found = local_repo(cwd)
    target = normalize_repo(option(args, "-R", "--repo") or "") or (found[1] if found else None)
    if target is None:
        return "PR 대상 레포를 읽지 못했다"
    if target not in config:
        return None
    if found is None or found[1] != target:
        return f"{target} PR을 그 레포 작업 트리 밖에서 만들려 한다"
    root = found[0]
    branch = option(args, "-H", "--head") or run_git(root, "branch", "--show-current")
    if not branch or branch != run_git(root, "branch", "--show-current"):
        return "현재 브랜치가 아닌 브랜치의 PR이라 작업 트리로 확인할 수 없다"
    base = option(args, "-B", "--base")
    base_ref = f"origin/{base}" if base else (run_git(root, "rev-parse", "--abbrev-ref", "origin/HEAD") or "origin/main")
    changed = run_git(root, "diff", "--name-only", f"{base_ref}...HEAD")
    if changed is not None and changed and all(is_doc(p) for p in changed.splitlines()):
        return None
    failures = check_local(root, target, branch, config[target])
    return "\n".join(failures) or None


def judge_merge(args: list[str], cwd: Path, config: dict) -> str | None:
    found = local_repo(cwd)
    target = normalize_repo(option(args, "-R", "--repo") or "") or (found[1] if found else None)
    if target is None:
        return "PR 대상 레포를 읽지 못했다"
    if target not in config:
        return None
    view = ["gh", "pr", "view", *([positional(args)] if positional(args) else []), "-R", target,
            "--json", "headRefName,headRefOid,files"]
    try:
        data = json.loads(subprocess.run(view, cwd=cwd if cwd.is_dir() else None, check=True,
                                         capture_output=True, text=True, timeout=20).stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return f"PR 정보를 읽지 못했다: {exc}"
    files = [f.get("path", "") for f in data.get("files") or []]
    if files and all(is_doc(p) for p in files):
        return None
    failures = check_remote(target, data["headRefName"], data["headRefOid"], config[target])
    return "\n".join(failures) or None


def decide(event: dict, harness: str) -> dict:
    if event.get("tool_name") not in ("Bash", "shell", "exec_command", "local_shell"):
        return {}
    tool_input = event.get("tool_input") or {}
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if isinstance(command, list):
        command = shlex.join(command)
    if not isinstance(command, str) or "gh" not in command:
        return {}
    cwd = Path(str(event.get("cwd") or tool_input.get("workdir") or os.getcwd())).expanduser()
    calls = gh_invocations(command)
    if not calls:
        return {}
    problems = []
    config = load_config()
    for action, args, cd_target in calls:
        where = (cwd / cd_target).expanduser() if cd_target else cwd
        if action == "create":
            problems.append(judge_create(args, where, config))
        else:
            problems.append(judge_merge(args, where, config))
    problems = [p for p in problems if p]
    if not problems:
        return {}
    reason = ("증거 문턱: 필수 검사 기록이 없거나 낡았다.\n" + "\n".join(problems) +
              "\n기록: dev 스킬 scripts/gate.py run --condition <이름>, 끝 리뷰는 gate.py review --report <파일>.")
    if harness == "claude":
        reason += " 예외로 진행하려면 사용자가 이 확인 창에서 승인한다."
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                       "permissionDecisionReason": reason}}
    reason += " 예외는 사용자에게 확인받고, 사용자가 직접 실행한다."
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


def hook(harness: str) -> int:
    try:
        if verify is None:
            raise RuntimeError(f"verify 모듈을 불러오지 못했다: {VERIFY_IMPORT_ERROR!r}")
        output = decide(json.loads(sys.stdin.read() or "{}"), harness)
    except Exception as exc:  # 판정 오류는 통과가 아니라 차단이다.
        output = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                         "permissionDecisionReason": f"증거 문턱 훅 오류로 막았다: {exc!r}"}}
    if output:
        print(json.dumps(output, ensure_ascii=False))
    return 0


def current(cwd: Path) -> tuple[Path, str, str, dict[str, list[str]]]:
    found = local_repo(cwd)
    if found is None:
        raise ValueError("origin이 GitHub인 레포 안에서 실행한다")
    root, name = found
    branch = run_git(root, "branch", "--show-current")
    if not branch:
        raise ValueError("브랜치를 읽지 못했다(detached HEAD)")
    conditions = load_config().get(name)
    if not conditions:
        raise ValueError(f"{config_path()}에 {name} 설정이 없다")
    return root, name, branch, conditions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("run", "review", "status", "hook"))
    parser.add_argument("--condition")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--harness", choices=("claude", "codex"), default="claude")
    parser.add_argument("--timeout", type=float, default=900)
    args = parser.parse_args()
    if args.action == "hook":
        return hook(args.harness)
    try:
        root, name, branch, conditions = current(Path.cwd())
        directory = evidence_dir(name, branch)
        if args.action == "status":
            failures = check_local(root, name, branch, conditions)
            for line in failures or [f"{len(required(conditions))}개 조건 모두 현재 코드 기준 기록 있음"]:
                print(line)
            print(f"기록 폴더: {directory}")
            return int(bool(failures))
        if args.action == "run":
            if args.condition not in conditions:
                raise ValueError(f"설정된 조건: {', '.join(conditions)}")
            result = verify.record(root, directory, args.condition, conditions[args.condition], timeout=args.timeout)
        else:
            report = args.report.expanduser().resolve() if args.report else None
            if report is None or report.is_relative_to(root):
                raise ValueError("--report는 레포 밖 보고 파일이어야 한다")
            result = verify.record(root, directory, REVIEW, [*REVIEW_COMMAND, str(report)])
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"증거 기록 실패: {exc}", file=sys.stderr)
        return 1
    print(f"{result['condition']}: {result['status']} — {directory}")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
