from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from creamcode.skills import SkillLoader, SkillMatcher, SkillRegistry, SkillLoadError


class TestSkillRegistry:
    def test_load_all_with_empty_dir(self, tmp_path):
        registry = SkillRegistry(tmp_path)
        registry.load_all()
        assert registry._skills == {}

    def test_load_all_discovers_skills(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test\n",
            encoding="utf-8",
        )
        registry = SkillRegistry(tmp_path)
        registry.load_all()
        assert "test-skill" in registry._skills
        skill = registry.get_skill("test-skill")
        assert skill is not None
        assert skill.name == "test-skill"

    def test_get_skill_returns_skill(self, tmp_path):
        skill_dir = tmp_path / "get-test"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: get-test\ndescription: Get test\n---\n\n# Get Test\n",
            encoding="utf-8",
        )
        registry = SkillRegistry(tmp_path)
        registry.load_all()
        skill = registry.get_skill("get-test")
        assert skill is not None
        assert skill.name == "get-test"

    def test_get_skill_returns_none_for_missing(self, tmp_path):
        registry = SkillRegistry(tmp_path)
        registry.load_all()
        skill = registry.get_skill("nonexistent")
        assert skill is None

    def test_find_matching_skills_returns_matches(self, tmp_path):
        skill_dir = tmp_path / "memory-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: memory-skill\ndescription: Memory persistence\n---\n\n# Memory\n",
            encoding="utf-8",
        )
        registry = SkillRegistry(tmp_path)
        registry.load_all()
        matches = registry.find_matching_skills("I need memory")
        assert len(matches) >= 1
        assert matches[0][0].name == "memory-skill"

    def test_find_matching_skills_respects_top_k(self, tmp_path):
        for i in range(5):
            skill_dir = tmp_path / f"skill-{i}"
            skill_dir.mkdir()
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(
                f"---\nname: skill-{i}\ndescription: Skill {i}\n---\n\n# Skill {i}\n",
                encoding="utf-8",
            )
        registry = SkillRegistry(tmp_path)
        registry.load_all()
        matches = registry.find_matching_skills("skill-0 skill-1 skill-2 skill-3 skill-4", top_k=2)
        assert len(matches) <= 2

    def test_find_matching_skills_sorted_by_score(self, tmp_path):
        skill_dir_high = tmp_path / "high-match"
        skill_dir_high.mkdir()
        skill_file = skill_dir_high / "SKILL.md"
        skill_file.write_text(
            "---\nname: high-match\ndescription: Memory persistence skill for long term storage\n---\n\n# High\n",
            encoding="utf-8",
        )
        skill_dir_low = tmp_path / "low-match"
        skill_dir_low.mkdir()
        skill_file = skill_dir_low / "SKILL.md"
        skill_file.write_text(
            "---\nname: low-match\ndescription: Memory usage for temporary storage\n---\n\n# Low\n",
            encoding="utf-8",
        )
        registry = SkillRegistry(tmp_path)
        registry.load_all()
        matches = registry.find_matching_skills("memory persistence long-term")
        assert len(matches) == 2
        high_score = next(s[1] for s in matches if s[0].name == "high-match")
        low_score = next(s[1] for s in matches if s[0].name == "low-match")
        assert high_score > low_score

    def test_reload_skill_updates_skill(self, tmp_path):
        skill_dir = tmp_path / "reload-test"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: reload-test\ndescription: Original\n---\n\n# Original\n",
            encoding="utf-8",
        )
        registry = SkillRegistry(tmp_path)
        registry.load_all()
        original = registry.get_skill("reload-test")
        assert original is not None
        assert original.description == "Original"

        skill_file.write_text(
            "---\nname: reload-test\ndescription: Updated\n---\n\n# Updated\n",
            encoding="utf-8",
        )
        reloaded = registry.reload_skill("reload-test")
        assert reloaded is not None
        assert reloaded.description == "Updated"

    def test_reload_skill_returns_none_for_missing(self, tmp_path):
        registry = SkillRegistry(tmp_path)
        registry.load_all()
        result = registry.reload_skill("nonexistent")
        assert result is None

    def test_reload_skill_handles_load_error(self, tmp_path):
        skill_dir = tmp_path / "error-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: error-skill\ndescription: Error skill\n---\n\n# Error\n",
            encoding="utf-8",
        )
        registry = SkillRegistry(tmp_path)
        registry.load_all()

        skill_file.unlink()

        result = registry.reload_skill("error-skill")
        assert result is None

    def test_load_all_clears_previous_skills(self, tmp_path):
        skill_dir = tmp_path / "first-load"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: first-load\ndescription: First load\n---\n\n# First\n",
            encoding="utf-8",
        )
        registry = SkillRegistry(tmp_path)
        registry.load_all()
        assert len(registry._skills) == 1

        skill_dir2 = tmp_path / "second-load"
        skill_dir2.mkdir()
        skill_file2 = skill_dir2 / "SKILL.md"
        skill_file2.write_text(
            "---\nname: second-load\ndescription: Second load\n---\n\n# Second\n",
            encoding="utf-8",
        )
        registry.load_all()
        assert len(registry._skills) == 2
        assert "first-load" in registry._skills
        assert "second-load" in registry._skills
