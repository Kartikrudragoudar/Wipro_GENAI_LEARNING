"""Embeddings module for storing and retrieving correction sessions by semantic similarity.

Uses ChromaDB as local vector store and LangChain embeddings for encoding.
"""

import logging
from typing import Any

from langchain_core.embeddings import Embeddings

from app.models import CorrectionAttempt

logger = logging.getLogger(__name__)

EMBEDDING_DESCRIPTION_TEMPLATE = "Language: {language} | Error: {error_message} | Bug: {bug_summary} | Fix strategy: {fix_strategy}"


class CorrectionEmbeddingStore:
    """Stores correction sessions as embeddings for semantic retrieval."""

    def __init__(self, embeddings: Embeddings, collection_name: str = "correction_sessions"):
        import chromadb

        self.embeddings = embeddings
        self.client = chromadb.Client()  # In-memory; use PersistentClient for disk
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def store_correction(
        self,
        session_id: str,
        language: str,
        error_message: str,
        bug_summary: str,
        fix_strategy: str,
        fixed_code: str,
        attempt: CorrectionAttempt,
    ) -> None:
        """Embed and store a correction attempt for future retrieval."""
        description = EMBEDDING_DESCRIPTION_TEMPLATE.format(
            language=language,
            error_message=error_message,
            bug_summary=bug_summary,
            fix_strategy=fix_strategy,
        )
        vector = self.embeddings.embed_query(description)
        doc_id = f"{session_id}_attempt_{attempt.attempt_number}"

        self.collection.upsert(
            ids=[doc_id],
            embeddings=[vector],
            documents=[description],
            metadatas=[{
                "session_id": session_id,
                "language": language,
                "attempt_number": attempt.attempt_number,
                "status": attempt.status,
                "confidence_score": attempt.confidence_score,
                "bug_summary": bug_summary,
                "fixed_code_preview": fixed_code[:500],
            }],
        )
        logger.info("Stored embedding for %s", doc_id)

    def find_similar_corrections(
        self,
        language: str,
        error_message: str,
        code_snippet: str = "",
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Find similar past corrections by semantic similarity."""
        query_text = f"Language: {language} | Error: {error_message} | Code: {code_snippet[:200]}"
        vector = self.embeddings.embed_query(query_text)

        results = self.collection.query(
            query_embeddings=[vector],
            n_results=min(top_k, max(self.collection.count(), 1)),
            include=["documents", "metadatas", "distances"],
        )

        similar: list[dict[str, Any]] = []
        if results and results["metadatas"]:
            for i, metadata in enumerate(results["metadatas"][0]):
                similar.append({
                    "metadata": metadata,
                    "document": results["documents"][0][i] if results["documents"] else "",
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                })
        return similar

    def get_session_history(self, session_id: str) -> list[dict[str, Any]]:
        """Retrieve all stored attempts for a specific session."""
        results = self.collection.get(
            where={"session_id": session_id},
            include=["documents", "metadatas"],
        )
        entries: list[dict[str, Any]] = []
        if results and results["metadatas"]:
            for i, metadata in enumerate(results["metadatas"]):
                entries.append({
                    "metadata": metadata,
                    "document": results["documents"][i] if results["documents"] else "",
                })
        return entries

    @property
    def total_stored(self) -> int:
        return self.collection.count()
