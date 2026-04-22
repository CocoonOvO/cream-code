from __future__ import annotations

from pathlib import Path

import pytest

from creamcode.skills import Skill, SkillMatcher


class TestSkillMatcher:
    def test_match_returns_empty_for_empty_prompt(self):
        skills = [
            Skill(
                name="test",
                description="test description",
                location=Path("/test"),
                instructions="test",
                keywords=["test"],
            )
        ]
        matcher = SkillMatcher(skills)
        result = matcher.match("")
        assert result == []

    def test_match_returns_empty_for_whitespace_prompt(self):
        skills = [
            Skill(
                name="test",
                description="test description",
                location=Path("/test"),
                instructions="test",
                keywords=["test"],
            )
        ]
        matcher = SkillMatcher(skills)
        result = matcher.match("   ")
        assert result == []

    def test_match_returns_empty_for_no_skills(self):
        matcher = SkillMatcher([])
        result = matcher.match("test prompt")
        assert result == []

    def test_exact_keyword_match(self):
        skills = [
            Skill(
                name="memory-skill",
                description="Long-term memory persistence skill",
                location=Path("/memory"),
                instructions="Memory instructions",
                keywords=["memory", "persist", "long-term"],
            )
        ]
        matcher = SkillMatcher(skills)
        result = matcher.match("I need memory persistence")
        assert len(result) == 1
        skill, score = result[0]
        assert skill.name == "memory-skill"
        assert score > 0.0

    def test_partial_keyword_match(self):
        skills = [
            Skill(
                name="code-review",
                description="Code review and analysis",
                location=Path("/review"),
                instructions="Review instructions",
                keywords=["code", "review", "analysis"],
            )
        ]
        matcher = SkillMatcher(skills)
        result = matcher.match("review my code")
        assert len(result) == 1
        skill, score = result[0]
        assert skill.name == "code-review"

    def test_top_k_parameter(self):
        skills = [
            Skill(
                name=f"skill-{i}",
                description=f"Description for skill {i}",
                location=Path(f"/skill-{i}"),
                instructions=f"Instructions {i}",
                keywords=[f"keyword{i}"],
            )
            for i in range(5)
        ]
        matcher = SkillMatcher(skills)
        result = matcher.match("keyword0 keyword1 keyword2 keyword3 keyword4")
        assert len(result) <= 3

    def test_matches_sorted_by_score(self):
        skills = [
            Skill(
                name="low-match",
                description="Need to review some content",
                location=Path("/low"),
                instructions="Low match instructions",
                keywords=["review", "content"],
            ),
            Skill(
                name="high-match",
                description="Memory and persistence related",
                location=Path("/high"),
                instructions="High match instructions",
                keywords=["memory", "persist", "long-term"],
            ),
        ]
        matcher = SkillMatcher(skills)
        result = matcher.match("I need memory persistence")
        assert len(result) == 2
        high_match = next(s for s in result if s[0].name == "high-match")
        low_match = next(s for s in result if s[0].name == "low-match")
        assert high_match[1] > low_match[1]

    def test_no_match_returns_empty(self):
        skills = [
            Skill(
                name="specific-skill",
                description="Very specific skill",
                location=Path("/specific"),
                instructions="Specific instructions",
                keywords=["xyz123"],
            )
        ]
        matcher = SkillMatcher(skills)
        result = matcher.match("completely unrelated prompt here")
        assert result == []

    def test_special_characters_handling(self):
        skills = [
            Skill(
                name="special-test",
                description="Testing special chars: @#$%",
                location=Path("/special"),
                instructions="Special @#$%",
                keywords=["special", "test"],
            )
        ]
        matcher = SkillMatcher(skills)
        result = matcher.match("special @#$% characters")
        assert len(result) >= 1

    def test_chinese_description_keywords(self):
        skills = [
            Skill(
                name="chinese-skill",
                description="当用户输入开发时触发此技能",
                location=Path("/chinese"),
                instructions="Chinese instructions",
                keywords=["开发", "触发"],
            )
        ]
        matcher = SkillMatcher(skills)
        result = matcher.match("开发新项目")
        assert len(result) >= 1

    def test_multiple_skills_tie_breaking(self):
        skills = [
            Skill(
                name="skill-a",
                description="Common description text",
                location=Path("/a"),
                instructions="A",
                keywords=["common"],
            ),
            Skill(
                name="skill-b",
                description="Common description text",
                location=Path("/b"),
                instructions="B",
                keywords=["common"],
            ),
        ]
        matcher = SkillMatcher(skills)
        result = matcher.match("common")
        assert len(result) == 2
        scores = [r[1] for r in result]
        assert scores[0] == scores[1]
