from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from creamcode.skills import SkillLoader, SkillLoadError


class TestSkillLoader:
    def test_discover_skills_finds_nothing_when_dir_empty(self, tmp_path):
        loader = SkillLoader(tmp_path)
        skills = loader.discover_skills()
        assert skills == []

    def test_discover_skills_finds_nothing_when_dir_missing(self, tmp_path):
        nonexistent = tmp_path / "nonexistent"
        loader = SkillLoader(nonexistent)
        skills = loader.discover_skills()
        assert skills == []

    def test_discover_skills_finds_skill_with_skill_md(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test Skill\n",
            encoding="utf-8",
        )
        loader = SkillLoader(tmp_path)
        skills = loader.discover_skills()
        assert len(skills) == 1
        assert skills[0].name == "test-skill"
        assert skills[0].description == "A test skill"

    def test_discover_skills_ignores_dirs_without_skill_md(self, tmp_path):
        skill_dir = tmp_path / "no-skill"
        skill_dir.mkdir()
        (skill_dir / "README.md").write_text("Not a skill", encoding="utf-8")
        loader = SkillLoader(tmp_path)
        skills = loader.discover_skills()
        assert skills == []

    def test_discover_skills_finds_multiple_skills(self, tmp_path):
        for name in ["skill-a", "skill-b", "skill-c"]:
            skill_dir = tmp_path / name
            skill_dir.mkdir()
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(
                f"---\nname: {name}\ndescription: Description of {name}\n---\n\n# {name}\n",
                encoding="utf-8",
            )
        loader = SkillLoader(tmp_path)
        skills = loader.discover_skills()
        assert len(skills) == 3
        names = {s.name for s in skills}
        assert names == {"skill-a", "skill-b", "skill-c"}

    def test_load_skill_file_not_found(self, tmp_path):
        loader = SkillLoader(tmp_path)
        with pytest.raises(SkillLoadError, match="not found"):
            loader.load_skill(tmp_path / "nonexistent" / "SKILL.md")

    def test_parse_skill_file_with_frontmatter(self, tmp_path):
        skill_file = tmp_path / "SKILL.md"
        content = """---
name: frontmatter-skill
description: A skill with frontmatter
keywords: test, frontmatter
---

# Frontmatter Skill

This is the body content.
"""
        skill_file.write_text(content, encoding="utf-8")
        loader = SkillLoader(tmp_path)
        skill = loader.parse_skill_file(skill_file)
        assert skill.name == "frontmatter-skill"
        assert skill.description == "A skill with frontmatter"
        assert "frontmatter" in skill.keywords

    def test_parse_skill_file_without_frontmatter(self, tmp_path):
        skill_dir = tmp_path / "simple-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        content = """# Simple Skill

This skill has no frontmatter.
"""
        skill_file.write_text(content, encoding="utf-8")
        loader = SkillLoader(tmp_path)
        skill = loader.parse_skill_file(skill_file)
        assert skill.name == "simple-skill"
        assert skill.description == ""

    def test_parse_skill_file_with_title_fallback(self, tmp_path):
        skill_dir = tmp_path / "custom-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        content = """# My Custom Skill

Some content here.
"""
        skill_file.write_text(content, encoding="utf-8")
        loader = SkillLoader(tmp_path)
        skill = loader.parse_skill_file(skill_file)
        assert "My Custom Skill" in skill.instructions

    def test_parse_skill_file_read_error(self, tmp_path):
        skill_dir = tmp_path / "error-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("test", encoding="utf-8")

        with patch.object(Path, "read_text", side_effect=OSError("Simulated read error")):
            loader = SkillLoader(tmp_path)
            with pytest.raises(SkillLoadError, match="Failed to read"):
                loader.parse_skill_file(skill_file)

    def test_keyword_extraction(self, tmp_path):
        skill_dir = tmp_path / "keyword-test"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        content = """---
name: keyword-test
description: Testing keyword extraction from description text
---

# Keyword Test
"""
        skill_file.write_text(content, encoding="utf-8")
        loader = SkillLoader(tmp_path)
        skill = loader.parse_skill_file(skill_file)
        assert len(skill.keywords) > 0
        assert "testing" in skill.keywords or "keyword" in skill.keywords
