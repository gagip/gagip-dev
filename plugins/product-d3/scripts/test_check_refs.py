import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "check_refs.py"


def run(plugin: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(plugin)], capture_output=True, text=True)


def write(root: Path, rel: str, text: str = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def make_plugin(tmp_path: Path) -> Path:
    plugin = tmp_path / "plug"
    write(plugin, "skills/a/SKILL.md", "# a\n")
    write(plugin, "references/shared.md", "x\n")
    return plugin


def test_missing_plugin_dir_exits_2(tmp_path):
    result = run(tmp_path / "nope")

    assert result.returncode == 2
    assert result.stderr.strip()


def test_plugin_without_markdown_exits_2(tmp_path):
    (tmp_path / "plug").mkdir()

    assert run(tmp_path / "plug").returncode == 2


def test_link_relative_to_file_folder_resolves(tmp_path):
    plugin = make_plugin(tmp_path)
    write(plugin, "skills/a/SKILL.md", "[r](../../references/shared.md)\n")

    assert run(plugin).returncode == 0


def test_backtick_path_resolves_against_skill_folder(tmp_path):
    plugin = make_plugin(tmp_path)
    write(plugin, "skills/a/references/deep/x.md", "")
    write(plugin, "skills/a/SKILL.md", "see `references/deep/x.md`\n")
    write(plugin, "skills/a/references/other.md", "see `references/deep/x.md`\n")

    assert run(plugin).returncode == 0


def test_backtick_path_resolves_against_plugin_root(tmp_path):
    plugin = make_plugin(tmp_path)
    write(plugin, "skills/a/SKILL.md", "see `references/shared.md`\n")

    assert run(plugin).returncode == 0


def test_dotdot_path_escaping_the_plugin_is_reported_with_line(tmp_path):
    plugin = make_plugin(tmp_path)
    write(plugin, "skills/a/SKILL.md", "ok\n\n`../../../common/references/x.md`\n")
    write(tmp_path, "common/references/x.md", "exists outside the plugin")

    result = run(plugin)

    assert result.returncode == 1
    assert "안 풀림 skills/a/SKILL.md:3 ../../../common/references/x.md" in result.stdout


def test_dotdot_path_does_not_fall_back_to_plugin_root(tmp_path):
    plugin = make_plugin(tmp_path)
    write(plugin, "skills/a/SKILL.md", "[x](../references/shared.md)\n")

    result = run(plugin)

    assert result.returncode == 1
    assert "../references/shared.md" in result.stdout


def test_markdown_link_to_sibling_skill_missing_in_plugin_is_reported(tmp_path):
    plugin = make_plugin(tmp_path)
    write(plugin, "skills/a/SKILL.md", "[w](../work-plan/SKILL.md)\n")

    assert run(plugin).returncode == 1


def test_skipped_forms_are_not_reported(tmp_path):
    plugin = make_plugin(tmp_path)
    write(
        plugin,
        "skills/a/SKILL.md",
        "\n".join([
            "[u](https://x.y/z.md)",
            "[abs](/etc/a.md)",
            "`~/a/b.md`",
            "`<name>/x.md`",
            "`skills/*/SKILL.md`",
            "`docs/features/x/PRD.md`",
            "`src/a.py`",
            "[p](PRD.md)",
            "[p](PRODUCT.md)",
            "[anchor](#top)",
            "`no-slash.md`",
        ]),
    )
    write(plugin, "CHANGELOG.md", "`gone/away.md`\n")

    result = run(plugin)

    assert result.returncode == 0, result.stdout


def test_paths_inside_code_fences_are_ignored(tmp_path):
    plugin = make_plugin(tmp_path)
    write(plugin, "skills/a/SKILL.md", "```\n`gone/away.md`\n[x](gone/away.md)\n```\n")

    assert run(plugin).returncode == 0
