"""Vector embedding storage and retrieval for TypeDB 3.x entities.

Stores embeddings as JSON-serialized strings in TypeDB attributes,
and provides cosine similarity search for semantic entity matching.

From ARCHITECTURE_PLAN.md Phase 1 Task: typedb_embeddings.py (P1).
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any

from src.typedb.client import TypeDBClient

logger = logging.getLogger(__name__)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        raise ValueError(f"Vector dimension mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingStore:
    """Store and retrieve vector embeddings for TypeDB entities.

    Embeddings are stored as JSON-serialized strings in the
    `embedding-json` attribute of enterprise-entity instances.
    Similarity search is performed client-side after retrieval.
    """

    def __init__(self, client: TypeDBClient) -> None:
        self.client = client

    async def store_embedding(
        self,
        entity_id: str,
        embedding: list[float],
    ) -> None:
        """Store an embedding vector for an entity."""
        embedding_json = json.dumps(embedding)
        typeql = f"""
        match
            $e isa enterprise-entity, has entity-id "{entity_id}";
        insert
            $e has embedding-json '{embedding_json}';
        """
        await self.client.write(typeql)
        logger.info(
            "Stored embedding for entity %s (dim=%d)", entity_id, len(embedding)
        )

    async def get_embedding(self, entity_id: str) -> list[float] | None:
        """Retrieve the embedding vector for an entity."""
        typeql = f"""
        match
            $e isa enterprise-entity, has entity-id "{entity_id}",
                has embedding-json $emb;
        """
        results = await self.client.query(typeql)
        if not results:
            return None
        emb_str = results[0].get("emb", "")
        if not emb_str:
            return None
        return json.loads(emb_str)

    async def get_all_embeddings(self) -> dict[str, list[float]]:
        """Retrieve all entity embeddings from the database."""
        typeql = """
        match
            $e isa enterprise-entity, has entity-id $id,
                has embedding-json $emb;
        """
        results = await self.client.query(typeql)
        embeddings: dict[str, list[float]] = {}
        for result in results:
            eid = result.get("id", "")
            emb_str = result.get("emb", "")
            if eid and emb_str:
                embeddings[eid] = json.loads(emb_str)
        return embeddings

    async def find_similar(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Find entities with embeddings most similar to the query vector.

        Performs client-side cosine similarity search over all stored
        embeddings. For production-scale workloads, consider using a
        dedicated vector index.

        Args:
            query_embedding: The query vector.
            top_k: Maximum number of results.
            threshold: Minimum similarity score (0.0 to 1.0).

        Returns:
            List of dicts with entity_id and similarity score, sorted
            by descending similarity.
        """
        all_embeddings = await self.get_all_embeddings()
        scored: list[tuple[float, str]] = []

        for entity_id, embedding in all_embeddings.items():
            try:
                score = cosine_similarity(query_embedding, embedding)
            except ValueError:
                logger.warning(
                    "Dimension mismatch for entity %s, skipping", entity_id
                )
                continue
            if score >= threshold:
                scored.append((score, entity_id))

        scored.sort(reverse=True)
        return [
            {"entity_id": eid, "similarity": score}
            for score, eid in scored[:top_k]
        ]

    async def delete_embedding(self, entity_id: str) -> None:
        """Remove the embedding for an entity.

        TypeDB 3.x: uses 'delete attr of $entity;' syntax.
        """
        typeql = f"""
        match
            $e isa enterprise-entity, has entity-id "{entity_id}",
                has embedding-json $emb;
        delete embedding-json of $e;
        """
        await self.client.write(typeql)
        logger.info("Deleted embedding for entity %s", entity_id)
