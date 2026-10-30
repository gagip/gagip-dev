"""검증 명령을 실행하고 저장소의 현재 내용에 연결된 증거를 남긴다.

이 기록은 실행 추적이지 서명된 증명이 아니다. 명령의 적절성·사용자의 확인 출처는 사람이
검토한다. Git이 무시하는 파일, 외부 데이터·서비스 상태는 내용 지문에 포함하지 않는다.
"""
from __future__ import annotations

import argparse
import fcntl
import math
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from uuid import uuid4



def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def fingerprint(repo: Path) -> str:
    """커밋·스테이징 여부 대신 실제 파일 내용·실행 권한·심볼릭 링크를 식별한다."""
    digest = hashlib.sha256()
    names = set(git(repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0"))
    for raw in sorted(names - {b""}):
        path = repo / os.fsdecode(raw)
        if not path.is_symlink() and not path.exists():
            continue  # 삭제를 스테이징하기 전후에도 실제 작업트리는 같다.
        digest.update(len(raw).to_bytes(8, "big") + raw)
        if path.is_symlink():
            value = b"link:" + os.fsencode(os.readlink(path))
        elif path.is_file():
            value = (b"executable:" if path.stat().st_mode & 0o111 else b"file:") + path.read_bytes()
        else:
            raise ValueError(f"파일로 식별할 수 없는 경로(서브모듈 등): {path}")
        digest.update(hashlib.sha256(value).digest())
    return digest.hexdigest()


def inputs(repo: Path, directory: Path) -> tuple[Path, Path]:
    repo = repo.expanduser().resolve()
    directory = directory.expanduser().resolve()
    root = Path(os.fsdecode(git(repo, "rev-parse", "--show-toplevel")).strip()).resolve()
    if root != repo:
        raise ValueError("repo는 저장소 루트여야 한다")
    if directory.is_relative_to(repo):
        raise ValueError("검증 기록은 저장소 밖 작업 폴더에 둔다")
    return repo, directory


def key(condition: str) -> str:
    if not condition.strip():
        raise ValueError("검증 조건은 비어 있을 수 없다")
    return hashlib.sha256(condition.encode()).hexdigest()


def save(path: Path, record: dict) -> None:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        tmp = Path(stream.name)
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    tmp.replace(path)


def _record(repo: Path, directory: Path, condition: str, command: list[str], *, timeout: float = 120,
           source: str = "", observation: str = "") -> dict:
    repo, directory = inputs(repo, directory)
    identifier = key(condition)
    human = "사람 확인" in condition
    if human and (command or not source.strip() or not observation.strip()):
        raise ValueError("사람 확인은 실제 사용자 확인의 출처와 관찰을 적는다")
    if not human and (not command or source or observation):
        raise ValueError("자동 검증 조건에는 실행 명령이 필요하다")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout은 양수여야 한다")
    before = fingerprint(repo)
    result = {"schema": 1, "condition": condition, "repo": str(repo),
              "head": git(repo, "rev-parse", "HEAD").decode().strip(),
              "started_at": datetime.now(timezone.utc).isoformat(),
              "before": before, "kind": "human" if human else "command"}
    if human:
        result.update(source=source, observation=observation, status="confirmed")
    else:
        log = directory / f"{identifier}-{uuid4().hex}.log"
        result.update(command=command, log=log.name, exit_code=None, status="running")
        save(directory / f"{identifier}.json", result)  # 중단돼도 이전 성공을 재사용하지 않는다.
        with log.open("wb") as stream:
            try:
                process = subprocess.Popen(command, cwd=repo, stdout=stream, stderr=subprocess.STDOUT,
                                           start_new_session=(os.name == "posix"))
                try:
                    result["exit_code"] = process.wait(timeout=timeout)
                    result["status"] = "passed" if process.returncode == 0 else "failed"
                except subprocess.TimeoutExpired:
                    if os.name == "posix":
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                    process.wait()
                    result["status"] = "timeout"
                except BaseException:
                    if process.poll() is None:
                        try:
                            if os.name == "posix":
                                os.killpg(process.pid, signal.SIGKILL)
                            else:
                                process.kill()
                        except ProcessLookupError:
                            pass
                    process.wait()
                    raise
            except OSError as exc:
                result["status"] = "not-run"
                stream.write(str(exc).encode())
        result["log_sha256"] = hashlib.sha256(log.read_bytes()).hexdigest()
    result["after"] = fingerprint(repo)
    if before != result["after"]:
        result["status"] = "changed"
    save(directory / f"{identifier}.json", result)
    return result


def record(repo: Path, directory: Path, condition: str, command: list[str], *, timeout: float = 120,
           source: str = "", observation: str = "") -> dict:
    repo, directory = inputs(repo, directory)
    identifier = key(condition)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / f"{identifier}.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("같은 조건의 검증이 실행 중이다 — 종료 뒤 재실행한다") from None
        return _record(repo, directory, condition, command, timeout=timeout,
                       source=source, observation=observation)


def check(repo: Path, directory: Path, conditions: list[str]) -> list[str]:
    """조건별 최신 기록만 본다. 실패 전의 성공 기록으로 되돌아가지 않는다."""
    try:
        repo, directory = inputs(repo, directory)
        if not conditions:
            raise ValueError("확인할 완료 조건을 지정해야 한다")
        for condition in conditions:
            key(condition)
        current = fingerprint(repo)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return [f"검증 증거를 읽을 수 없음: {exc}"]
    failures = []
    for condition in conditions:
        identifier = key(condition)
        try:
            lock_path = directory / f"{identifier}.lock"
            if lock_path.exists():
                with lock_path.open("r") as lock:
                    try:
                        fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
                    except BlockingIOError:
                        raise ValueError("검증 실행 중 — 이전 성공 기록을 재사용할 수 없음") from None
            item = json.loads((directory / f"{identifier}.json").read_text())
            if not isinstance(item, dict):
                raise ValueError("기록은 객체여야 한다")
            if item.get("schema") != 1 or item.get("condition") != condition or item.get("repo") != str(repo):
                raise ValueError("조건·저장소·형식이 현재 요청과 다름")
            if item.get("before") != current or item.get("after") != current:
                raise ValueError("검증 이후 코드가 바뀌었거나 검증 중 변경됨")
            if "사람 확인" in condition:
                if item.get("kind") != "human" or item.get("status") != "confirmed" or not item.get("source") or not item.get("observation"):
                    raise ValueError("실제 사용자 확인의 출처·관찰이 없음")
            else:
                if item.get("kind") != "command" or item.get("status") != "passed" or item.get("exit_code") != 0 or not item.get("command"):
                    raise ValueError("성공한 실행 기록이 없음")
                name = item.get("log", "")
                if not isinstance(name, str) or not name or Path(name).name != name:
                    raise ValueError("로그 파일명이 잘못됨")
                log = directory / name
                if hashlib.sha256(log.read_bytes()).hexdigest() != item.get("log_sha256"):
                    raise ValueError("실행 로그가 기록과 다름")
        except (OSError, ValueError, TypeError) as exc:
            failures.append(f"검증 조건 {condition}: {exc}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "check", "confirm"))
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--condition", action="append", required=True)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--source", default="")
    parser.add_argument("--observation", default="")
    argv = sys.argv[1:]
    separator = argv.index("--") if "--" in argv else len(argv)
    args = parser.parse_args(argv[:separator])
    command = argv[separator + 1:]
    try:
        if args.action == "check":
            if command or args.source or args.observation:
                raise ValueError("check에는 명령·사람 확인을 섞지 않는다")
            failures = check(args.repo, args.evidence, args.condition)
            for failure in failures:
                print(failure)
            if not failures:
                print(f"{len(args.condition)}개 조건의 현재 증거 확인")
            return int(bool(failures))
        if len(args.condition) != 1:
            raise ValueError("실행·사람 확인은 조건 하나씩 기록한다")
        human = "사람 확인" in args.condition[0]
        if human != (args.action == "confirm"):
            raise ValueError("사람 확인 조건은 confirm으로, 자동 검증은 run으로 실행한다")
        result = record(args.repo, args.evidence, args.condition[0], command,
                        timeout=args.timeout, source=args.source, observation=args.observation)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"검증 기록 실패: {exc}", file=sys.stderr)
        return 1
    print(f"{args.condition[0]}: {result['status']} — {args.evidence}")
    return 0 if result["status"] in ("passed", "confirmed") else 1


if __name__ == "__main__":
    sys.exit(main())
