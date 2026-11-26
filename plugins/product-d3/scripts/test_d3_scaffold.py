import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "d3_scaffold.py"
TEMPLATES = Path(__file__).parent.parent / "assets" / "templates"


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args], capture_output=True, text=True
    )


def test_init_creates_product_docs_and_agents_with_verify_command(tmp_path):
    result = run(tmp_path, "init", "--verify-command", "npm test")

    assert result.returncode == 0
    assert (tmp_path / "PRODUCT.md").read_text() == (TEMPLATES / "PRODUCT.md").read_text()
    assert (tmp_path / "docs/.gitkeep").exists()
    agents = (tmp_path / "AGENTS.md").read_text()
    assert "검증 명령: npm test" in agents
    assert "{verify_command}" not in agents
    assert not (tmp_path / "CLAUDE.md").exists()


def test_init_without_verify_command_writes_none_marker(tmp_path):
    run(tmp_path, "init")

    assert "검증 명령: 없음" in (tmp_path / "AGENTS.md").read_text()


def test_init_never_overwrites_existing_files(tmp_path):
    (tmp_path / "PRODUCT.md").write_text("mine")
    (tmp_path / "AGENTS.md").write_text("my agents")

    result = run(tmp_path, "init")

    assert (tmp_path / "PRODUCT.md").read_text() == "mine"
    assert (tmp_path / "AGENTS.md").read_text() == "my agents"
    assert "건너뜀 PRODUCT.md" in result.stdout
    assert "건너뜀 AGENTS.md" in result.stdout


def test_init_proposes_merge_when_existing_agents_lacks_marker(tmp_path):
    (tmp_path / "AGENTS.md").write_text("my agents")

    result = run(tmp_path, "init", "--verify-command", "make test")

    assert "병합 제안" in result.stdout
    assert "검증 명령: make test" in result.stdout
    assert (tmp_path / "AGENTS.md").read_text() == "my agents"


def test_init_reports_already_present_when_agents_has_marker(tmp_path):
    (tmp_path / "AGENTS.md").write_text("x\n<!-- product-d3 start -->\ny")

    result = run(tmp_path, "init")

    assert "이미 있음" in result.stdout
    assert "병합 제안" not in result.stdout


def test_init_skips_gitkeep_when_docs_has_files(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/a.md").write_text("")

    run(tmp_path, "init")

    assert not (tmp_path / "docs/.gitkeep").exists()


def test_dry_run_writes_nothing_but_reports(tmp_path):
    result = run(tmp_path, "--dry-run", "init")

    assert "만듦 PRODUCT.md" in result.stdout
    assert list(tmp_path.iterdir()) == []


def test_feature_fills_name_into_prd_template(tmp_path):
    result = run(tmp_path, "feature", "user-login")

    assert result.returncode == 0
    prd = (tmp_path / "docs/features/user-login/PRD.md").read_text()
    assert prd.startswith("# user-login\n")


def test_feature_does_not_overwrite_existing_prd(tmp_path):
    path = tmp_path / "docs/features/a/PRD.md"
    path.parent.mkdir(parents=True)
    path.write_text("mine")

    result = run(tmp_path, "feature", "a")

    assert path.read_text() == "mine"
    assert "건너뜀" in result.stdout


def test_feature_rejects_invalid_slug_with_exit_2(tmp_path):
    result = run(tmp_path, "feature", "Bad_Slug")

    assert result.returncode == 2
    assert result.stderr.strip()
    assert not (tmp_path / "docs").exists()


def test_experiment_creates_readme_and_log_with_heading(tmp_path):
    result = run(tmp_path, "experiment", "fast-path", "--feature", "search", "--date", "2026-01-02")

    assert result.returncode == 0
    readme = (tmp_path / "experiments/2026-01-02-fast-path/README.md").read_text()
    assert "「2026-01-02 fast-path」" in readme
    assert "docs/features/search/EXPERIMENTS.md" in readme
    log = (tmp_path / "docs/features/search/EXPERIMENTS.md").read_text()
    assert log.startswith("# Experiments\n")
    assert "## 2026-01-02 fast-path" in log


def test_experiment_appends_to_existing_log_without_duplicating_same_entry(tmp_path):
    run(tmp_path, "experiment", "a", "--feature", "f", "--date", "2026-01-02")
    run(tmp_path, "experiment", "b", "--feature", "f", "--date", "2026-01-02")
    run(tmp_path, "experiment", "a", "--feature", "f", "--date", "2026-01-02")

    log = (tmp_path / "docs/features/f/EXPERIMENTS.md").read_text()

    assert log.count("## 2026-01-02 a") == 1
    assert log.count("## 2026-01-02 b") == 1


def test_experiment_rejects_bad_date_with_exit_2(tmp_path):
    result = run(tmp_path, "experiment", "a", "--feature", "f", "--date", "01-02")

    assert result.returncode == 2
