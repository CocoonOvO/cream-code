from __future__ import annotations

from pathlib import Path

import pytest

from creamcode.skills import Skill


class TestSkillDataclass:
    def test_create_skill_with_required_fields(self):
        skill = Skill(
            name="test-skill",
            description="A test skill",
            location=Path("/path/to/skill"),
            instructions="# Test Skill\n\nThis is a test.",
        )
        assert skill.name == "test-skill"
        assert skill.description == "A test skill"
        assert skill.location == Path("/path/to/skill")
        assert skill.instructions == "# Test Skill\n\nThis is a test."
        assert skill.keywords == []

    def test_create_skill_with_keywords(self):
        skill = Skill(
            name="memory-skill",
            description="Long-term memory persistence",
            location=Path("/path/to/memory"),
            instructions="Memory instructions",
            keywords=["memory", "persist", "long-term"],
        )
        assert len(skill.keywords) == 3
        assert "memory" in skill.keywords

    def test_skill_attribute_access(self):
        skill = Skill(
            name="access-test",
            description="Testing attribute access",
            location=Path("/test"),
            instructions="Test",
        )
        assert hasattr(skill, "name")
        assert hasattr(skill, "description")
        assert hasattr(skill, "location")
        assert hasattr(skill, "instructions")
        assert hasattr(skill, "keywords")

    def test_skill_default_keywords_is_empty_list(self):
        skill = Skill(
            name="default-test",
            description="Test",
            location=Path("/test"),
            instructions="Test",
        )
        assert skill.keywords == []
        assert isinstance(skill.keywords, list)


class TestSkillSerialization:
    def test_to_dict(self):
        skill = Skill(
            name="serialize-test",
            description="Testing serialization",
            location=Path("/path/to/skill"),
            instructions="# Test",
            keywords=["test", "serialize"],
        )
        result = skill.to_dict()
        assert result["name"] == "serialize-test"
        assert result["description"] == "Testing serialization"
        assert Path(result["location"]) == Path("/path/to/skill")
        assert result["instructions"] == "# Test"
        assert result["keywords"] == ["test", "serialize"]

    def test_from_dict(self):
        data = {
            "name": "deserialize-test",
            "description": "Testing deserialization",
            "location": "/path/to/skill",
            "instructions": "# Test",
            "keywords": ["test", "deserialize"],
        }
        skill = Skill.from_dict(data)
        assert skill.name == "deserialize-test"
        assert skill.description == "Testing deserialization"
        assert skill.location == Path("/path/to/skill")
        assert skill.instructions == "# Test"
        assert skill.keywords == ["test", "deserialize"]

    def test_roundtrip_serialization(self):
        original = Skill(
            name="roundtrip-test",
            description="Testing roundtrip",
            location=Path("/path/to/roundtrip"),
            instructions="# Roundtrip",
            keywords=["test", "roundtrip"],
        )
        data = original.to_dict()
        restored = Skill.from_dict(data)
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.location == original.location
        assert restored.instructions == original.instructions
        assert restored.keywords == original.keywords

    def test_from_dict_without_keywords(self):
        data = {
            "name": "no-keywords-test",
            "description": "Test without keywords",
            "location": "/path/to/test",
            "instructions": "Test",
        }
        skill = Skill.from_dict(data)
        assert skill.keywords == []
