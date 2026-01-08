"""
AI Agents for Command Center
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.total_cost = 0.0
        self.total_requests = 0

    @abstractmethod
    async def execute(
        self, task: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute the agent's task"""
        pass

    def track_usage(self, input_tokens: int, output_tokens: int, model: str = "claude"):
        """Track usage and costs"""
        from config.settings import settings

        if "claude" in model.lower():
            cost = (input_tokens / 1_000_000) * settings.CLAUDE_INPUT_COST + (
                output_tokens / 1_000_000
            ) * settings.CLAUDE_OUTPUT_COST
        else:  # GPT
            cost = (input_tokens / 1_000_000) * settings.GPT4_INPUT_COST + (
                output_tokens / 1_000_000
            ) * settings.GPT4_OUTPUT_COST

        self.total_cost += cost
        self.total_requests += 1

        return cost

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            "name": self.name,
            "total_requests": self.total_requests,
            "total_cost": self.total_cost,
            "avg_cost": self.total_cost / max(self.total_requests, 1),
        }
