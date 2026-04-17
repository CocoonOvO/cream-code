from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BaseTool(ABC):
    name: str
    description: str
    parameters: dict

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        pass
