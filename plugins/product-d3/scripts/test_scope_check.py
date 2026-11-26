import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent / "scope_check.py"


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True, capture_output=True,
    )


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--base", "base", *args],
        capture_output=True, text=True,
    )


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, "src/app.py", "x = 1\n")
    write(tmp_path, "tests/test_app.py", "def test_a():\n    assert 1\n    assert 2\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "init")
    git(tmp_path, "tag", "base")
    return tmp_path


def test_no_changes_passes(repo):
    assert run(repo).returncode == 0


def test_missing_base_ref_exits_2(repo):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(repo), "--base", "nope"], capture_output=True, text=True
    )

    assert result.returncode == 2
    assert result.stderr.strip()


def test_non_git_folder_exits_2(tmp_path):
    result = run(tmp_path)

    assert result.returncode == 2
    assert result.stderr.strip()


def test_file_outside_allow_globs_is_error(repo):
    write(repo, "src/app.py", "x = 2\n")
    write(repo, "other/new.py", "y = 1\n")

    result = run(repo, "--allow", "src/*")

    assert result.returncode == 1
    assert "오류 other/new.py 범위 밖" in result.stdout
    assert "src/app.py 범위 밖" not in result.stdout


def test_without_allow_any_change_is_in_scope(repo):
    write(repo, "src/app.py", "x = 2\n")

    assert run(repo).returncode == 0


def test_deleted_test_file_is_error(repo):
    (repo / "tests/test_app.py").unlink()

    result = run(repo)

    assert result.returncode == 1
    assert "테스트 파일이 삭제됨" in result.stdout


@pytest.mark.parametrize("marker", [
    "@pytest.mark.skip", "@skip", "it.skip('x', f)", "xit('x', f)", "xdescribe('x', f)",
    "@Disabled", "@Ignore", "t.Skip(\"x\")",
])
def test_added_skip_marker_in_committed_change_is_error(repo, marker):
    write(repo, "tests/test_app.py", f"def test_a():\n    assert 1\n    assert 2\n{marker}\n")
    git(repo, "commit", "-q", "-am", "skip")

    result = run(repo)

    assert result.returncode == 1
    assert "skip 표시가 추가됨" in result.stdout


def test_skip_marker_in_untracked_new_test_file_is_error(repo):
    write(repo, "tests/test_new.py", "import pytest\n@pytest.mark.skip\ndef test_b():\n    assert 1\n")

    result = run(repo)

    assert result.returncode == 1
    assert "tests/test_new.py" in result.stdout


def test_skip_marker_in_non_test_file_is_ignored(repo):
    write(repo, "src/app.py", "x.skip(1)\n")

    assert run(repo).returncode == 0


def test_fewer_assertions_is_warning_not_error(repo):
    write(repo, "tests/test_app.py", "def test_a():\n    assert 1\n")

    result = run(repo)

    assert result.returncode == 0
    assert "경고 tests/test_app.py" in result.stdout


def test_dependency_file_change_is_warning(repo):
    write(repo, "package.json", "{}\n")

    result = run(repo)

    assert result.returncode == 0
    assert "경고 package.json" in result.stdout


def test_rename_of_test_file_is_not_deletion(repo):
    git(repo, "mv", "tests/test_app.py", "tests/test_renamed.py")

    result = run(repo)

    assert "삭제" not in result.stdout
    assert result.returncode == 0


def test_non_ascii_untracked_test_file_with_skip_is_error(repo):
    write(repo, "tests/test_한글.py", "import pytest\n@pytest.mark.skip\ndef test_b():\n    assert 1\n")

    result = run(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "test_한글.py" in result.stdout


def test_non_ascii_path_matches_allow_glob(repo):
    write(repo, "src/문서.py", "y = 2\n")

    result = run(repo, "--allow", "src/*")

    assert result.returncode == 0, result.stdout + result.stderr

