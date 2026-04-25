from __future__ import annotations

import re
from collections import Counter

from .skill import Skill


class SkillMatcher:
    def __init__(self, skills: list[Skill]) -> None:
        self.skills = skills

    def match(self, prompt: str, top_k: int = 3) -> list[tuple[Skill, float]]:
        if not prompt.strip() or not self.skills:
            return []

        prompt_lower = prompt.lower()
        prompt_tokens = self._tokenize(prompt_lower)

        scored: list[tuple[Skill, float]] = []
        for skill in self.skills:
            score = self._calculate_score(prompt_lower, prompt_tokens, skill)
            if score > 0.0:
                scored.append((skill, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _tokenize(self, text: str) -> list[str]:
        tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_-]*", text.lower())
        return tokens

    def _calculate_score(
        self, prompt_lower: str, prompt_tokens: list[str], skill: Skill
    ) -> float:
        keyword_score = self._keyword_match_score(prompt_lower, skill)
        desc_score = self._description_similarity(prompt_tokens, skill)
        combined = keyword_score * 0.6 + desc_score * 0.4
        return min(1.0, combined)

    def _keyword_match_score(self, prompt_lower: str, skill: Skill) -> float:
        if not skill.keywords:
            return 0.0
        matches = 0
        for keyword in skill.keywords:
            if keyword.lower() in prompt_lower:
                matches += 1
        return matches / len(skill.keywords)

    def _description_similarity(
        self, prompt_tokens: list[str], skill: Skill
    ) -> float:
        if not prompt_tokens:
            return 0.0
        desc_tokens = self._tokenize(skill.description.lower())
        if not desc_tokens:
            return 0.0
        prompt_counter = Counter(prompt_tokens)
        desc_counter = Counter(desc_tokens)
        common = set(prompt_tokens) & set(desc_tokens)
        if not common:
            return 0.0
        similarity = sum(min(prompt_counter[t], desc_counter[t]) for t in common)
        max_len = max(len(prompt_tokens), len(desc_tokens))
        return similarity / max_len if max_len > 0 else 0.0
