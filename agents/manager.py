"""
Manager Agent - Orchestrates specialist agents
"""

import asyncio
from typing import Dict, List, Any, Optional
from anthropic import Anthropic
import logging

from agents import BaseAgent
from agents.researcher import ResearchAgent
from agents.rag import RAGAgent
from agents.code_review import CodeReviewAgent
from config.settings import settings

logger = logging.getLogger(__name__)


class ManagerAgent(BaseAgent):
    """
    Manager agent that:
    1. Analyzes user request
    2. Determines which specialist agents to use
    3. Delegates tasks in parallel
    4. Synthesizes results
    """

    ROUTING_PROMPT = """You are a manager AI that routes user requests to specialist agents.

Available specialists:
1. **research_agent**: Web search, current information, data analysis
2. **rag_agent**: Search internal documents, answer questions about uploaded files
3. **code_review_agent**: Analyze code, find bugs, suggest improvements

Analyze this user request and determine which specialists to use.

User request: {query}

Respond with JSON:
{{
    "specialists": ["research_agent", "rag_agent"],  // which agents to use
    "tasks": {{
        "research_agent": "specific task for research agent",
        "rag_agent": "specific task for RAG agent"
    }},
    "reasoning": "why you chose these agents"
}}

Only use agents that are actually needed. If one agent can handle it, only use one."""

    SYNTHESIS_PROMPT = """You are a synthesizer AI that combines results from multiple specialist agents.

User's original question: {query}

Specialist results:
{results}

Synthesize these results into a coherent, comprehensive answer.
- Highlight agreements between agents
- Note any contradictions
- Provide a clear, actionable answer
- Cite which agent provided which information"""

    def __init__(self):
        super().__init__(
            name="Manager Agent",
            description="Orchestrates specialist agents and synthesizes results"
        )

        # Initialize specialist agents
        self.research_agent = ResearchAgent()
        self.rag_agent = RAGAgent()
        self.code_review_agent = CodeReviewAgent()

        # Map agent names to instances
        self.agents = {
            "research_agent": self.research_agent,
            "rag_agent": self.rag_agent,
            "code_review_agent": self.code_review_agent
        }

        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def execute(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute user request through specialist agents

        Args:
            task: User's request/question
            context: Optional context (uploaded files, etc.)

        Returns:
            Dict with answer, agent_results, metadata
        """
        logger.info(f"Manager received task: {task[:100]}...")

        try:
            # Step 1: Route to specialists
            routing = await self._route_request(task, context)

            logger.info(f"Routing: {routing['specialists']}")

            # Step 2: Execute specialists in parallel
            agent_results = await self._execute_specialists(routing, context)

            # Step 3: Synthesize results
            final_answer = await self._synthesize_results(task, agent_results)

            # Step 4: Collect metadata
            metadata = self._collect_metadata(routing, agent_results)

            return {
                "answer": final_answer,
                "agent_results": agent_results,
                "routing": routing,
                "metadata": metadata,
                "success": True
            }

        except Exception as e:
            logger.error(f"Manager execution failed: {e}", exc_info=True)
            return {
                "answer": f"I encountered an error: {str(e)}",
                "error": str(e),
                "success": False
            }

    async def _route_request(self, query: str, context: Optional[Dict]) -> Dict[str, Any]:
        """Determine which agents to use"""
        prompt = self.ROUTING_PROMPT.format(query=query)

        response = self.client.messages.create(
            model=settings.DEFAULT_LLM_MODEL,
            max_tokens=1024,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )

        # Track usage
        self.track_usage(
            response.usage.input_tokens,
            response.usage.output_tokens
        )

        # Parse response
        import json
        routing_text = response.content[0].text

        # Extract JSON (handle markdown code blocks)
        if "```json" in routing_text:
            routing_text = routing_text.split("```json")[1].split("```")[0].strip()
        elif "```" in routing_text:
            routing_text = routing_text.split("```")[1].split("```")[0].strip()

        routing = json.loads(routing_text)

        return routing

    async def _execute_specialists(
        self,
        routing: Dict[str, Any],
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Execute specialist agents in parallel"""

        specialists = routing.get("specialists", [])
        tasks_map = routing.get("tasks", {})

        # Create async tasks
        async_tasks = []
        agent_names = []

        for agent_name in specialists:
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                task = tasks_map.get(agent_name, "")

                async_tasks.append(agent.execute(task, context))
                agent_names.append(agent_name)
            else:
                logger.warning(f"Unknown agent: {agent_name}")

        # Execute in parallel
        results = await asyncio.gather(*async_tasks, return_exceptions=True)

        # Combine results
        agent_results = {}
        for name, result in zip(agent_names, results):
            if isinstance(result, Exception):
                agent_results[name] = {
                    "error": str(result),
                    "success": False
                }
            else:
                agent_results[name] = result

        return agent_results

    async def _synthesize_results(
        self,
        original_query: str,
        agent_results: Dict[str, Any]
    ) -> str:
        """Synthesize specialist results into final answer"""

        # Format results for synthesis
        formatted_results = []
        for agent_name, result in agent_results.items():
            if result.get("success"):
                formatted_results.append(
                    f"**{agent_name}**:\n{result.get('answer', result.get('result', 'No response'))}"
                )
            else:
                formatted_results.append(
                    f"**{agent_name}**: Failed - {result.get('error', 'Unknown error')}"
                )

        results_text = "\n\n".join(formatted_results)

        prompt = self.SYNTHESIS_PROMPT.format(
            query=original_query,
            results=results_text
        )

        response = self.client.messages.create(
            model=settings.DEFAULT_LLM_MODEL,
            max_tokens=2048,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}]
        )

        # Track usage
        self.track_usage(
            response.usage.input_tokens,
            response.usage.output_tokens
        )

        return response.content[0].text

    def _collect_metadata(
        self,
        routing: Dict[str, Any],
        agent_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Collect metadata about execution"""

        # Calculate total cost
        total_cost = self.total_cost
        for agent in self.agents.values():
            total_cost += agent.total_cost

        # Count successful/failed agents
        successful = sum(1 for r in agent_results.values() if r.get("success"))
        failed = len(agent_results) - successful

        return {
            "total_cost": total_cost,
            "agents_used": list(agent_results.keys()),
            "agents_successful": successful,
            "agents_failed": failed,
            "routing_reasoning": routing.get("reasoning", "")
        }


# Test the manager
if __name__ == "__main__":
    async def test():
        manager = ManagerAgent()

        # Test query
        result = await manager.execute(
            "What are the latest developments in AI safety? Also search our docs for any related policies."
        )

        print("\n" + "="*70)
        print("FINAL ANSWER:")
        print("="*70)
        print(result["answer"])

        print("\n" + "="*70)
        print("METADATA:")
        print("="*70)
        for key, value in result["metadata"].items():
            print(f"{key}: {value}")

    asyncio.run(test())