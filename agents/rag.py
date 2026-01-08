"""
RAG Agent - Document search and Q&A using ChromaDB
"""

from typing import Dict, Any, Optional, List
from anthropic import Anthropic
import logging

from agents import BaseAgent
from services.document_service import DocumentService
from config.settings import settings

logger = logging.getLogger(__name__)


class RAGAgent(BaseAgent):
    """
    RAG specialist for document search and Q&A
    Uses ChromaDB for vector storage and retrieval
    """

    SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the provided context from documents.

Instructions:
- Answer questions using ONLY the information from the provided context
- If the context doesn't contain enough information to answer, say so clearly
- Cite the source documents when providing information
- Be concise but comprehensive
- If multiple sources provide relevant information, synthesize them"""

    def __init__(self, vector_db_path: str = None):
        super().__init__(
            name="RAG Agent",
            description="Document search and Q&A specialist"
        )

        # Use settings path if not provided
        self.vector_db_path = vector_db_path or settings.VECTOR_DB_PATH

        # Initialize document service
        try:
            self.doc_service = DocumentService(persist_directory=self.vector_db_path)
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            logger.info(f"RAG agent initialized with {self.doc_service.get_stats()['total_documents']} chunks")
        except Exception as e:
            logger.error(f"Failed to initialize RAG agent: {e}")
            self.doc_service = None
            self.client = None

    def _format_context(self, results: List[Dict[str, Any]]) -> str:
        """Format search results into context for the LLM"""
        if not results:
            return "No relevant documents found."

        context_parts = []
        for i, result in enumerate(results, 1):
            source = result["metadata"].get("source", "Unknown")
            text = result["text"]
            context_parts.append(f"[Document {i}: {source}]\n{text}")

        return "\n\n---\n\n".join(context_parts)

    async def execute(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute document search and Q&A

        Args:
            task: The question/query to answer
            context: Optional additional context

        Returns:
            Dict with answer, sources, and success status
        """
        logger.info(f"RAG agent executing: {task[:100]}...")

        # Check if service is available
        if not self.doc_service or not self.client:
            return {
                "answer": "RAG service not available. Please check configuration.",
                "success": False
            }

        # Check if there are any documents
        stats = self.doc_service.get_stats()
        if stats["total_documents"] == 0:
            return {
                "answer": "No documents have been indexed yet. Please upload documents first using the Documents tab.",
                "success": False
            }

        try:
            # Search for relevant documents
            search_results = self.doc_service.search(query=task, n_results=5)

            if not search_results:
                return {
                    "answer": "No relevant documents found for your query.",
                    "sources": [],
                    "success": True
                }

            # Format context from search results
            doc_context = self._format_context(search_results)

            # Build prompt for Claude
            user_prompt = f"""Based on the following documents, please answer this question:

**Question:** {task}

**Documents:**
{doc_context}

Please provide a comprehensive answer based on the documents above."""

            # Call Claude for answer generation
            response = self.client.messages.create(
                model=settings.DEFAULT_LLM_MODEL,
                max_tokens=2048,
                temperature=0.3,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )

            # Track usage
            self.track_usage(
                response.usage.input_tokens,
                response.usage.output_tokens
            )

            answer = response.content[0].text

            # Extract unique sources
            sources = list(set(
                result["metadata"].get("source", "Unknown")
                for result in search_results
            ))

            # Format answer with sources
            formatted_answer = answer
            if sources:
                formatted_answer += "\n\n**Sources:**\n"
                for i, source in enumerate(sources, 1):
                    formatted_answer += f"{i}. {source}\n"

            return {
                "answer": formatted_answer,
                "sources": sources,
                "chunks_used": len(search_results),
                "success": True
            }

        except Exception as e:
            logger.error(f"RAG agent failed: {e}", exc_info=True)
            return {
                "answer": f"Document search failed: {str(e)}",
                "error": str(e),
                "success": False
            }
