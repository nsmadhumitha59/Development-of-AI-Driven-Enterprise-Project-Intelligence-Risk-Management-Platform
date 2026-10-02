from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseAgent(ABC):
    """
    Abstract Base Class for Multi-Agent System Architecture.
    Designed for seamless future expansion in upcoming milestones.
    """
    def __init__(self, agent_name: str, description: str):
        self.agent_name = agent_name
        self.description = description

    @abstractmethod
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent task workflow."""
        pass

    def get_info(self) -> Dict[str, Any]:
        """Return agent identity and capabilities."""
        return {
            "name": self.agent_name,
            "description": self.description
        }
