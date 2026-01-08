"""
Research Agent - Web search and data analysis
Wraps Week 3's research assistant
"""

import asyncio
from typing import Dict, Any, Optional
from anthropic import Anthropic
import logging
import os

from agents import BaseAgent
from config.settings import settings

logger = logging.getLogger(__name__)

# Import Tavily for web search
try:
    from tavily import TavilyClient

    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    logger.warning("Tavily not available - web search disabled")


class ResearchAgent(BaseAgent):
    """
    Research specialist using web search and analysis
    Based on Week 3's Research Assistant
    """

    TOOLS = [
        {
            "name": "web_search",
            "description": "Search the web for current information on any topic",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
        },
        {
            "name": "calculator",
            "description": "Perform mathematical calculations safely",
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate",
                    }
                },
                "required": ["expression"],
            },
        },
    ]

    def __init__(self):
        super().__init__(
            name="Research Agent", description="Web search and data analysis specialist"
        )

        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Initialize Tavily if available
        if TAVILY_AVAILABLE and settings.TAVILY_API_KEY:
            self.tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)
        else:
            self.tavily = None

    async def execute(
        self, task: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute research task using tools"""
        logger.info(f"Research agent executing: {task[:100]}...")

        messages = [{"role": "user", "content": task}]
        iterations = 0
        max_iterations = 5

        try:
            while iterations < max_iterations:
                iterations += 1

                response = self.client.messages.create(
                    model=settings.DEFAULT_LLM_MODEL,
                    max_tokens=4096,
                    tools=self.TOOLS,
                    messages=messages,
                )

                # Track usage
                self.track_usage(
                    response.usage.input_tokens, response.usage.output_tokens
                )

                # Check stop reason
                if response.stop_reason == "end_turn":
                    # Agent is done
                    final_text = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_text += block.text

                    return {
                        "answer": final_text,
                        "iterations": iterations,
                        "success": True,
                    }

                elif response.stop_reason == "tool_use":
                    # Execute tools
                    tool_results = []

                    for block in response.content:
                        if block.type == "tool_use":
                            result = await self._execute_tool(block.name, block.input)
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result,
                                }
                            )

                    # Add response and tool results to messages
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})

            # Max iterations reached
            return {
                "answer": "Research took too long (max iterations reached)",
                "iterations": iterations,
                "success": False,
            }

        except Exception as e:
            logger.error(f"Research agent failed: {e}", exc_info=True)
            return {
                "answer": f"Research failed: {str(e)}",
                "error": str(e),
                "success": False,
            }

    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        """Execute a tool and return results"""

        if tool_name == "web_search":
            return await self._web_search(tool_input["query"])

        elif tool_name == "calculator":
            return self._calculate(tool_input["expression"])

        else:
            return f"Unknown tool: {tool_name}"

    async def _web_search(self, query: str) -> str:
        """Search the web using Tavily"""
        if not self.tavily:
            return "Web search unavailable (Tavily not configured)"

        try:
            # Run in thread pool (Tavily is sync)
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, lambda: self.tavily.search(query, max_results=5)
            )

            # Format results
            formatted = f"Search results for: {query}\n\n"
            for i, result in enumerate(results.get("results", []), 1):
                formatted += f"{i}. {result['title']}\n"
                formatted += f"   {result['content'][:200]}...\n"
                formatted += f"   Source: {result['url']}\n\n"

            return formatted

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return f"Web search failed: {str(e)}"

    def _calculate(self, expression: str) -> str:
        """Safely evaluate mathematical expressions"""
        try:
            # Use AST for safe evaluation
            import ast
            import operator

            # Allowed operators
            operators = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }

            def eval_expr(node):
                if isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.BinOp):
                    return operators[type(node.op)](
                        eval_expr(node.left), eval_expr(node.right)
                    )
                elif isinstance(node, ast.UnaryOp):
                    return operators[type(node.op)](eval_expr(node.operand))
                else:
                    raise ValueError(f"Unsupported operation: {node}")

            tree = ast.parse(expression, mode="eval")
            result = eval_expr(tree.body)

            return f"{expression} = {result}"

        except Exception as e:
            return f"Calculation failed: {str(e)}"
