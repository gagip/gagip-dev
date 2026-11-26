import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "check_d3_docs.py"
PRODUCT_TITLES = ["Purpose", "Target Users", "Core Problems", "Vision", "Principles", "Non-goals", "Success Criteria"]
PRD_TITLES = ["Purpose", "Problem", "Scope", "Success Criteria"]


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args], capture_output=True, text=True
    )


def doc(titles: list[str], extra: str = "") -> str:
    body = "\n".join(f"## {t}\n<!-- 안내 -->\n" for t in titles)
    return f"# T\n\n{body}\n{extra}"


def make_product(root: Path, titles=PRODUCT_TITLES, extra: str = "") -> None:
    (root / "PRODUCT.md").write_text(doc(titles, extra))


def make_prd(root: Path, feature: str = "a", titles=PRD_TITLES, extra: str = "") -> Path:
    path = root / "docs/features" / feature / "PRD.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc(titles, extra))
    return path


def make_experiments(root: Path, text: str, feature: str = "a") -> None:
    path = root / "docs/features" / feature / "EXPERIMENTS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_complete_docs_with_empty_template_sections_pass(tmp_path):
    make_product(tmp_path)
    make_prd(tmp_path)

    result = run(tmp_path)

    assert result.returncode == 0, result.stdout
    assert "오류" not in result.stdout


def test_korean_headings_are_accepted(tmp_path):
    make_product(tmp_path, ["목적", "대상 사용자", "핵심 문제", "비전", "원칙", "비목표", "성공 기준"])
    make_prd(tmp_path, titles=["목적", "문제", "범위", "성공 기준"])

    assert run(tmp_path).returncode == 0


def test_missing_root_exits_2(tmp_path):
    result = run(tmp_path / "nope")

    assert result.returncode == 2
    assert result.stderr.strip()


def test_missing_product_file_is_error_exit_1(tmp_path):
    result = run(tmp_path)

    assert result.returncode == 1
    assert "오류 PRODUCT.md" in result.stdout


def test_each_missing_product_section_is_reported(tmp_path):
    for missing in PRODUCT_TITLES:
        make_product(tmp_path, [t for t in PRODUCT_TITLES if t != missing])

        result = run(tmp_path)

        assert result.returncode == 1, missing
        assert f"## {missing} 제목이 없다" in result.stdout


def test_missing_prd_section_is_error(tmp_path):
    make_product(tmp_path)
    make_prd(tmp_path, titles=["Purpose", "Problem", "Scope"])

    result = run(tmp_path)

    assert result.returncode == 1
    assert "docs/features/a/PRD.md:1" in result.stdout
    assert "Success Criteria" in result.stdout


def test_broken_relative_link_is_error_with_line_number(tmp_path):
    make_product(tmp_path)
    make_prd(tmp_path, extra="\n[x](missing.md)\n[ok](PRD.md)\n[web](https://a.b)\n[a](#top)\n[p](<path>)\n")

    result = run(tmp_path)

    assert result.returncode == 1
    assert "missing.md" in result.stdout
    assert "PRD.md)" not in result.stdout.replace("missing.md", "")
    assert result.stdout.count("링크 대상이 없다") == 1


def test_checklist_in_prd_is_warning_only(tmp_path):
    make_product(tmp_path)
    make_prd(tmp_path, extra="\n- [ ] 할 일\n- [x] 한 일\n")

    result = run(tmp_path)

    assert result.returncode == 0
    assert result.stdout.count("경고 ") == 2


def test_experiment_entry_without_required_lines_is_error(tmp_path):
    make_product(tmp_path)
    make_experiments(tmp_path, "# Experiments\n\n## 2026-01-01 x\n\n- 가설: a\n")

    result = run(tmp_path)

    assert result.returncode == 1
    for name in ["방법", "판정선", "결과", "판정"]:
        assert f"{name} 줄이 없다" in result.stdout
    assert "가설 줄이 없다" not in result.stdout


def test_result_without_threshold_is_error(tmp_path):
    make_product(tmp_path)
    make_experiments(
        tmp_path,
        "# Experiments\n\n## 2026-01-01 x\n\n- 가설: a\n- 방법: b\n- 판정선: <!-- 먼저 적는다 -->\n- 결과: 3건 통과\n- 판정:\n",
    )

    result = run(tmp_path)

    assert result.returncode == 1
    assert "판정선 없이 결과를 적음" in result.stdout


def test_filled_template_entry_with_empty_values_passes(tmp_path):
    make_product(tmp_path)
    make_experiments(
        tmp_path,
        "# Experiments\n\n## 2026-01-01 x\n\n- 가설:\n- 방법:\n- 판정선: <!-- 먼저 -->\n- 표본·기간:\n- 결과:\n- 판정: <!-- 통과 -->\n",
    )

    assert run(tmp_path).returncode == 0
