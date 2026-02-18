"""
Agent Framework — Ason Verification Platform
Liberty Center One — Internal Agents Only

ZERO EXTERNAL APIs.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class Agent(ABC):
    """
    Base class for all internal agents.
    """
    
    @abstractmethod
    def metadata(self) -> Dict[str, str]:
        """
        Return agent metadata.
        Must include: name, description, version, role.
        """
        pass

    @abstractmethod
    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute the agent's logic.
        
        Args:
            input_data: The specific input for the agent (e.g., {"request": "feature description"})
            context: Optional context (e.g., user info, project state)
            
        Returns:
            Dict containing the agent's output.
        """
        pass


class AgentRegistry:
    """
    Registry for internal agents.
    """
    def __init__(self):
        self._agents: Dict[str, Agent] = {}

    def register(self, agent: Agent):
        meta = agent.metadata()
        name = meta.get("name")
        if not name:
            raise ValueError("Agent missing name in metadata")
        self._agents[name] = agent

    def get(self, name: str) -> Optional[Agent]:
        return self._agents.get(name)

    def list_agents(self) -> List[Dict[str, str]]:
        return [a.metadata() for a in self._agents.values()]

# Global registry
agent_registry = AgentRegistry()
