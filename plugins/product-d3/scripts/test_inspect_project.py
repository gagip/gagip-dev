import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "inspect_project.py"


def run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True)


def report(root: Path) -> dict:
    result = run(root)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_folder_with_only_git_and_ds_store_is_new(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref")
    (tmp_path / ".DS_Store").write_text("")

    assert report(tmp_path)["mode"] == "new"


def test_folder_with_a_file_is_existing(tmp_path):
    (tmp_path / "main.py").write_text("")

    assert report(tmp_path)["mode"] == "existing"


def test_missing_root_exits_2_with_reason_on_stderr(tmp_path):
    result = run(tmp_path / "nope")

    assert result.returncode == 2
    assert result.stderr.strip()


def test_files_map_reports_path_or_null(tmp_path):
    (tmp_path / "AGENTS.md").write_text("")

    files = report(tmp_path)["files"]

    assert files["AGENTS.md"] == "AGENTS.md"
    assert files["PRODUCT.md"] is None
    assert files["CLAUDE.md"] is None
    assert files["README.md"] is None


def test_feature_prds_are_listed(tmp_path):
    (tmp_path / "docs/features/login").mkdir(parents=True)
    (tmp_path / "docs/features/login/PRD.md").write_text("")
    (tmp_path / "docs/features/empty").mkdir(parents=True)

    assert report(tmp_path)["feature_prds"] == ["docs/features/login/PRD.md"]


def test_test_dirs_skip_excluded_folders_and_respect_depth(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "src/test").mkdir(parents=True)
    (tmp_path / "node_modules/pkg/tests").mkdir(parents=True)
    (tmp_path / "a/b/c/d/tests").mkdir(parents=True)
    (tmp_path / "app/src/androidTest").mkdir(parents=True)

    test_dirs = report(tmp_path)["test_dirs"]

    assert "tests" in test_dirs
    assert "src/test" in test_dirs
    assert "app/src/androidTest" in test_dirs
    assert not any("node_modules" in d for d in test_dirs)
    assert "a/b/c/d/tests" not in test_dirs


def test_build_files_lists_only_root_files(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "settings.gradle.kts").write_text("")
    (tmp_path / "App.csproj").write_text("")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub/go.mod").write_text("")

    assert report(tmp_path)["build_files"] == ["App.csproj", "package.json", "settings.gradle.kts"]


def test_verify_commands_from_npm_scripts_and_makefile(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"test": "x", "dev": "y", "lint": "z"}}))
    (tmp_path / "Makefile").write_text("test:\n\techo\nbuild:\n\techo\n")

    commands = {c["command"]: c["source"] for c in report(tmp_path)["verify_commands"]}

    assert commands == {
        "npm run lint": "package.json",
        "npm run test": "package.json",
        "make test": "Makefile",
    }


def test_verify_commands_for_python_rust_go_gradle(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "Cargo.toml").write_text("")
    (tmp_path / "go.mod").write_text("")
    (tmp_path / "build.gradle").write_text("")

    commands = {c["command"] for c in report(tmp_path)["verify_commands"]}

    assert commands == {"python3 -m pytest", "cargo test", "go test ./...", "./gradlew test"}


def test_python_tests_dir_without_pyproject_suggests_pytest(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_a.py").write_text("")

    commands = [c["command"] for c in report(tmp_path)["verify_commands"]]

    assert commands == ["python3 -m pytest"]
