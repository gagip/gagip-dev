"""정상 스킬은 통과하고, 위반을 주입하면 각각 잡히는지 확인한다."""
from pathlib import Path
import tempfile
import unittest

import lint_skill

GOOD_BODY = "# 예시\n\n본문이다.\n"


def make_skill(root, *, name="demo-skill", dirname=None, description="무엇을 하고 언제 쓰는지 적는다.",
               body=GOOD_BODY, files=None):
    skill = root / (dirname or name)
    skill.mkdir(parents=True, exist_ok=True)
    desc_line = f"description: {description}" if description is not None else ""
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\n{desc_line}\n---\n\n{body}", encoding="utf-8")
    for rel, content in (files or {}).items():
        path = skill / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return skill


class LintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def problems(self, **kw):
        return lint_skill.lint(make_skill(self.root, **kw))

    def assertFlagged(self, problems, fragment):
        self.assertTrue(any(fragment in p for p in problems), f"{fragment!r} 없음: {problems}")

    def test_clean_skill_passes(self):
        self.assertEqual([], self.problems())

    def test_folded_description_is_read(self):
        skill = self.root / "folded"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "---\nname: folded\n# 주석\ndescription: >\n  첫 줄이다.\n  둘째 줄이다.\nallowed-tools: Read\n---\n본문\n",
            encoding="utf-8")
        self.assertEqual([], lint_skill.lint(skill))
        fields = lint_skill.parse_frontmatter(
            "name: folded\ndescription: >\n  첫 줄이다.\n  둘째 줄이다.\nallowed-tools: Read")
        self.assertEqual("첫 줄이다. 둘째 줄이다.", fields["description"])
        self.assertEqual("Read", fields["allowed-tools"])

    def test_missing_frontmatter(self):
        skill = self.root / "bare"
        skill.mkdir()
        (skill / "SKILL.md").write_text("# 제목만\n", encoding="utf-8")
        self.assertFlagged(lint_skill.lint(skill), "frontmatter")

    def test_name_rules(self):
        self.assertFlagged(self.problems(name="Bad_Name"), "소문자·숫자·하이픈")
        self.assertFlagged(self.root_problems("a" * 65), "64자")
        self.assertFlagged(self.root_problems("my-claude-helper"), "예약어")
        self.assertFlagged(self.problems(name="demo-two", dirname="other-dir"), "디렉터리명")

    def root_problems(self, name):
        return lint_skill.lint(make_skill(self.root, name=name))

    def test_description_rules(self):
        self.assertFlagged(self.problems(description=None), "description이 비어")
        self.assertFlagged(self.problems(description="가" * 1025), "1024자")
        self.assertFlagged(self.problems(description="쓰임은 <b>굵게</b> 한다"), "XML 태그")

    def test_description_at_limit_passes(self):
        self.assertEqual([], self.problems(description="가" * 1024))

    def test_body_line_limit(self):
        self.assertEqual([], self.problems(name="body-ok", body="줄\n" * 499))
        self.assertFlagged(self.problems(name="body-long", body="줄\n" * 500), "500줄")

    def test_backslash_path(self):
        self.assertFlagged(self.problems(body="실행: scripts\\helper.py\n"), "백슬래시")

    def test_broken_link(self):
        self.assertFlagged(self.problems(body="[가이드](references/missing.md)\n"), "링크 대상이 없다")

    def test_links_in_code_and_urls_are_ignored(self):
        body = "[문서](https://example.com/a.md)\n`[x](nope.md)`\n```\n[y](nope2.md)\n```\n[맨위](#top)\n"
        self.assertEqual([], self.problems(body=body))

    def test_nested_reference_depth(self):
        problems = self.problems(
            body="[a](references/a.md)\n",
            files={"references/a.md": "[b](b.md)\n", "references/b.md": "끝\n"})
        self.assertFlagged(problems, "한 단계까지만")

    def test_flat_references_pass(self):
        problems = self.problems(
            body="[a](references/a.md) [b](references/b.md)\n",
            files={"references/a.md": "내용\n", "references/b.md": "내용\n"})
        self.assertEqual([], problems)

    def test_long_reference_needs_toc(self):
        long_text = "# 제목\n" + "줄\n" * 120
        problems = self.problems(body="[a](references/a.md)\n", files={"references/a.md": long_text})
        self.assertFlagged(problems, "목차")

    def test_long_reference_with_toc_passes(self):
        long_text = "# 제목\n\n## 목차\n- 가\n\n" + "줄\n" * 120
        problems = self.problems(body="[a](references/a.md)\n", files={"references/a.md": long_text})
        self.assertEqual([], problems)

    def test_short_reference_needs_no_toc(self):
        problems = self.problems(body="[a](references/a.md)\n", files={"references/a.md": "줄\n" * 100})
        self.assertEqual([], problems)

    def test_discover_skips_hidden_and_eval_runs(self):
        make_skill(self.root, name="real-skill")
        make_skill(self.root / ".hidden", name="hidden-skill")
        make_skill(self.root / "x-eval-runs", name="run-skill")
        found = [p.name for p in lint_skill.discover(self.root)]
        self.assertEqual(["real-skill"], found)


if __name__ == "__main__":
    unittest.main()
