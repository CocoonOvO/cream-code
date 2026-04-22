from __future__ import annotations

from pathlib import Path

from .loader import SkillLoader, SkillLoadError
from .matcher import SkillMatcher
from .skill import Skill


class SkillRegistry:
    def __init__(self, skills_dir: Path | None = None) -> None:
        if skills_dir is None:
            skills_dir = Path.home() / ".creamcode" / "skills"
        self.loader = SkillLoader(skills_dir)
        self.matcher = SkillMatcher([])
        self._skills: dict[str, Skill] = {}

    def load_all(self) -> None:
        discovered = self.loader.discover_skills()
        self._skills.clear()
        for skill in discovered:
            self._skills[skill.name] = skill
        self.matcher = SkillMatcher(list(self._skills.values()))

    def get_skill(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def find_matching_skills(
        self, prompt: str, top_k: int = 3
    ) -> list[tuple[Skill, float]]:
        return self.matcher.match(prompt, top_k)

    def reload_skill(self, name: str) -> Skill | None:
        skill = self._skills.get(name)
        if skill is None:
            return None
        try:
            reloaded = self.loader.load_skill(skill.location / "SKILL.md")
            self._skills[name] = reloaded
            self.matcher = SkillMatcher(list(self._skills.values()))
            return reloaded
        except SkillLoadError:
            return None
