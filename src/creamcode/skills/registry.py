from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .loader import SkillLoader, SkillLoadError
from .matcher import SkillMatcher
from .skill import Skill

if TYPE_CHECKING:
    from ..core.event_bus import EventBus
    from ..tools.registry import ToolRegistry


class SkillRegistry:
    def __init__(
        self,
        skills_dir: Path | None = None,
        event_bus: 'EventBus | None' = None,
        tool_registry: 'ToolRegistry | None' = None,
    ) -> None:
        if skills_dir is None:
            skills_dir = Path.home() / ".creamcode" / "skills"
        self.loader = SkillLoader(skills_dir)
        self.matcher = SkillMatcher([])
        self._skills: dict[str, Skill] = {}
        self._event_bus = event_bus
        self._tool_registry = tool_registry

    def set_event_bus(self, event_bus: 'EventBus') -> None:
        """Set the event bus for skill events"""
        self._event_bus = event_bus

    def set_tool_registry(self, tool_registry: 'ToolRegistry') -> None:
        """Set the tool registry for skill tool access"""
        self._tool_registry = tool_registry

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

    def get_skill_instructions(self, name: str, context: dict[str, Any] | None = None) -> str | None:
        """
        Get skill instructions, optionally enhanced with context.
        
        Args:
            name: Skill name
            context: Optional context (available_tools, memory_state, etc.)
        """
        skill = self._skills.get(name)
        if skill is None:
            return None

        instructions = skill.instructions

        if context and self._event_bus:
            from ..types import Event
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._publish_skill_accessed(skill.name))
                else:
                    loop.run_until_complete(self._publish_skill_accessed(skill.name))
            except RuntimeError:
                pass

        return instructions

    async def _publish_skill_accessed(self, skill_name: str) -> None:
        """Publish event when a skill is accessed"""
        if self._event_bus:
            from ..types import Event
            await self._event_bus.publish(Event(
                name="skill.accessed",
                source="skill_registry",
                data={"skill_name": skill_name}
            ))
