"""
Document Service - Handles document ingestion and indexing with ChromaDB
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI

from config.settings import settings

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Service for document ingestion and indexing using ChromaDB
    """

    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200

    def __init__(self, persist_directory: str = "./data/vector_db"):
        self.persist_directory = persist_directory

        # Ensure directory exists
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )

        # Initialize OpenAI for embeddings
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

        logger.info(f"DocumentService initialized with {self.collection.count()} documents")

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        response = self.openai_client.embeddings.create(
            model=settings.DEFAULT_EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding

    def _chunk_text(self, text: str, filename: str) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks"""
        chunks = []

        # Simple chunking by character count with overlap
        start = 0
        chunk_id = 0

        while start < len(text):
            end = start + self.CHUNK_SIZE
            chunk_text = text[start:end]

            # Try to break at sentence or paragraph boundary
            if end < len(text):
                # Look for last period, newline, or space
                for char in ['\n\n', '\n', '. ', ' ']:
                    last_break = chunk_text.rfind(char)
                    if last_break > self.CHUNK_SIZE // 2:
                        chunk_text = chunk_text[:last_break + len(char)]
                        end = start + len(chunk_text)
                        break

            # Generate unique ID for chunk
            chunk_hash = hashlib.md5(f"{filename}:{chunk_id}:{chunk_text[:100]}".encode()).hexdigest()

            chunks.append({
                "id": chunk_hash,
                "text": chunk_text.strip(),
                "metadata": {
                    "source": filename,
                    "chunk_id": chunk_id,
                    "start_char": start,
                    "end_char": end
                }
            })

            chunk_id += 1
            start = end - self.CHUNK_OVERLAP

            if start < 0:
                start = 0

        return chunks

    def _extract_text_from_file(self, content: bytes, filename: str) -> str:
        """Extract text from file content based on file type"""
        extension = Path(filename).suffix.lower()

        if extension == ".txt":
            return content.decode("utf-8", errors="ignore")

        elif extension == ".md":
            return content.decode("utf-8", errors="ignore")

        elif extension == ".pdf":
            try:
                import io
                from pypdf import PdfReader

                pdf_file = io.BytesIO(content)
                reader = PdfReader(pdf_file)

                text_parts = []
                for page in reader.pages:
                    text_parts.append(page.extract_text() or "")

                return "\n\n".join(text_parts)

            except ImportError:
                logger.warning("pypdf not installed, cannot process PDF files")
                raise ValueError("PDF processing requires pypdf: pip install pypdf")
            except Exception as e:
                logger.error(f"Failed to extract PDF text: {e}")
                raise ValueError(f"Failed to process PDF: {str(e)}")

        else:
            raise ValueError(f"Unsupported file type: {extension}")

    async def ingest_document(
        self,
        content: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest a document: extract text, chunk, embed, and store in ChromaDB

        Args:
            content: File content as bytes
            filename: Original filename
            metadata: Optional additional metadata

        Returns:
            Dict with ingestion results
        """
        logger.info(f"Ingesting document: {filename}")

        try:
            # Extract text
            text = self._extract_text_from_file(content, filename)

            if not text.strip():
                return {
                    "success": False,
                    "error": "No text content found in document",
                    "filename": filename
                }

            # Chunk the text
            chunks = self._chunk_text(text, filename)
            logger.info(f"Created {len(chunks)} chunks from {filename}")

            # Generate embeddings and prepare for ChromaDB
            ids = []
            embeddings = []
            documents = []
            metadatas = []

            for chunk in chunks:
                embedding = self._get_embedding(chunk["text"])

                ids.append(chunk["id"])
                embeddings.append(embedding)
                documents.append(chunk["text"])

                chunk_metadata = chunk["metadata"].copy()
                if metadata:
                    chunk_metadata.update(metadata)
                metadatas.append(chunk_metadata)

            # Upsert to ChromaDB (handles duplicates)
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

            logger.info(f"Successfully indexed {len(chunks)} chunks from {filename}")

            return {
                "success": True,
                "filename": filename,
                "chunks_created": len(chunks),
                "total_documents": self.collection.count(),
                "text_length": len(text)
            }

        except Exception as e:
            logger.error(f"Failed to ingest document {filename}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "filename": filename
            }

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents

        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: Optional metadata filter

        Returns:
            List of matching documents with scores
        """
        # Generate query embedding
        query_embedding = self._get_embedding(query)

        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        formatted_results = []

        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted_results.append({
                    "id": doc_id,
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0
                })

        return formatted_results

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        return {
            "total_documents": self.collection.count(),
            "persist_directory": self.persist_directory
        }

    def list_sources(self) -> List[str]:
        """List all unique source files in the collection"""
        # Get all metadata
        results = self.collection.get(include=["metadatas"])

        sources = set()
        if results["metadatas"]:
            for metadata in results["metadatas"]:
                if metadata and "source" in metadata:
                    sources.add(metadata["source"])

        return sorted(list(sources))

    def delete_source(self, source: str) -> Dict[str, Any]:
        """Delete all chunks from a specific source file"""
        try:
            # Get IDs of documents from this source
            results = self.collection.get(
                where={"source": source},
                include=["metadatas"]
            )

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                return {
                    "success": True,
                    "deleted_chunks": len(results["ids"]),
                    "source": source
                }
            else:
                return {
                    "success": True,
                    "deleted_chunks": 0,
                    "source": source,
                    "message": "No documents found for this source"
                }

        except Exception as e:
            logger.error(f"Failed to delete source {source}: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": source
            }
