from __future__ import annotations

import re
from pathlib import Path

from .skill import Skill


class SkillLoadError(Exception):
    pass


class SkillLoader:
    def __init__(self, skills_dir: Path) -> None:
        self.skills_dir = skills_dir

    def discover_skills(self) -> list[Skill]:
        skills: list[Skill] = []
        if not self.skills_dir.exists():
            return skills
        for item in self.skills_dir.iterdir():
            if item.is_dir():
                skill_file = item / "SKILL.md"
                if skill_file.exists():
                    try:
                        skill = self.load_skill(skill_file)
                        skills.append(skill)
                    except SkillLoadError:
                        continue
        return skills

    def load_skill(self, skill_path: Path) -> Skill:
        if not skill_path.exists():
            raise SkillLoadError(f"Skill file not found: {skill_path}")
        return self.parse_skill_file(skill_path)

    def parse_skill_file(self, skill_file: Path) -> Skill:
        try:
            content = skill_file.read_text(encoding="utf-8")
        except Exception as e:
            raise SkillLoadError(f"Failed to read skill file: {e}")

        name: str | None = None
        description: str | None = None
        body: str = ""

        lines = content.splitlines()
        in_frontmatter = False
        frontmatter_lines: list[str] = []

        for line in lines:
            if line.strip() == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    in_frontmatter = False
                    continue

            if in_frontmatter:
                frontmatter_lines.append(line)
            else:
                if name is None and description is None and line.startswith("# "):
                    body = "\n".join(lines[lines.index(line):])
                    break

        if frontmatter_lines:
            for line in frontmatter_lines:
                match = re.match(r"^name:\s*(.+)$", line)
                if match:
                    name = match.group(1).strip()
                match = re.match(r"^description:\s*(.+)$", line)
                if match:
                    description = match.group(1).strip()

        if not name:
            name = skill_file.parent.name
        if not description:
            description = ""

        keywords = self._extract_keywords(description)

        return Skill(
            name=name,
            description=description,
            location=skill_file.parent,
            instructions=body.strip(),
            keywords=keywords,
        )

    def _extract_keywords(self, text: str) -> list[str]:
        words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_-]*", text.lower())
        stop_words = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
            "be", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "shall", "can", "need",
            "this", "that", "these", "those", "it", "its", "when", "which", "what",
        }
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        unique_keywords: list[str] = []
        seen: set[str] = set()
        for kw in keywords:
            if kw not in seen:
                unique_keywords.append(kw)
                seen.add(kw)
        return unique_keywords[:20]
