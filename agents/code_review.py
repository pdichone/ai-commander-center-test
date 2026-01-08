"""
Code Review Agent - Analyze code for bugs and improvements
Wraps Week 1's Code Reviewer
"""

from typing import Dict, Any, Optional
from anthropic import Anthropic
import logging

from agents import BaseAgent
from config.settings import settings

logger = logging.getLogger(__name__)


class CodeReviewAgent(BaseAgent):
    """
    Code review specialist
    Based on Week 1's AI Code Reviewer
    """

    REVIEW_PROMPT = """You are an expert code reviewer. Analyze this code for:

1. **Bugs**: Logic errors, edge cases, null pointer issues
2. **Security**: SQL injection, XSS, hardcoded secrets
3. **Performance**: Inefficient algorithms, memory leaks
4. **Best Practices**: Code style, naming, structure
5. **Improvements**: Suggestions for better code

Code to review:
{code}


Provide a structured review with:
- Overall assessment (1-10 score)
- Critical issues (must fix)
- Warnings (should fix)
- Suggestions (nice to have)
- Positive aspects (what's good)

Be specific and actionable."""

    def __init__(self):
        super().__init__(
            name="Code Review Agent", description="Code analysis and review specialist"
        )

        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def execute(
        self, task: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute code review"""
        logger.info(f"Code review agent executing...")

        # Extract code from task or context
        code = task
        if context and "code" in context:
            code = context["code"]

        try:
            prompt = self.REVIEW_PROMPT.format(code=code)

            response = self.client.messages.create(
                model=settings.DEFAULT_LLM_MODEL,
                max_tokens=4096,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )

            # Track usage
            self.track_usage(response.usage.input_tokens, response.usage.output_tokens)

            review = response.content[0].text

            return {"answer": review, "success": True}

        except Exception as e:
            logger.error(f"Code review failed: {e}", exc_info=True)
            return {
                "answer": f"Code review failed: {str(e)}",
                "error": str(e),
                "success": False,
            }
