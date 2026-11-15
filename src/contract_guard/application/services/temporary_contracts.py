"""Application operations for data that lives only in temporary contract storage."""

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import numpy as np

from contract_guard.application.services.chunking import ClauseChunker
from contract_guard.application.services.embedding import LocalEmbeddingService


class TemporaryContractStore(Protocol):
    """Application-facing contract-store operations."""
    settings: Any

    async def create_contract(self, contract: dict[str, Any]) -> None: ...
    async def get_contract(self, contract_id: str, owner_id: str) -> dict[str, Any]: ...
    async def update_contract(self, contract_id: str, owner_id: str, update: Any) -> dict[str, Any]: ...


class InvalidEmbeddingError(ValueError):
    """Raised when an embedding is not a finite 384-dimensional vector."""


class TemporaryContractService:
    """Coordinate processing of a single owner-scoped temporary contract."""

    _embedding_semaphores: dict[tuple[int, int], asyncio.Semaphore] = {}

    def __init__(self, repository: TemporaryContractStore, embedding_service: LocalEmbeddingService | None = None):
        """Initialize the service with replaceable persistence and embedding collaborators."""
        self.repository = repository
        self.embedding_service = embedding_service or LocalEmbeddingService()

    async def create(self, contract_id: str, owner_id: str, extracted: dict[str, Any]) -> dict[str, Any]:
        """Create a TTL-bound contract from a validated extraction result."""
        now = datetime.now(UTC)
        contract = {
            "contract_id": contract_id,
            "owner_id": str(owner_id),
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=self.repository.settings.contract_ttl_seconds)).isoformat(),
            "extracted_text": extracted["text"],
            "clauses": extracted["clauses"],
            "chunks": [],
            "embeddings": [],
            "analysis": {},
            "closing_metadata": extracted.get("closing_metadata", {}),
        }
        await self.repository.create_contract(contract)
        return contract

    async def classify(self, contract_id: str, owner_id: str, classifications: list[dict[str, Any]]) -> dict[str, Any]:
        """Persist classifications only while the contract remains valid."""
        def apply(contract: dict[str, Any]) -> None:
            by_id = {item["clause_id"]: item for item in classifications}
            for clause in contract["clauses"]:
                classification = by_id.get(clause.get("clause_id"))
                if classification is not None:
                    clause["taxonomy"] = classification
        return await self.repository.update_contract(contract_id, owner_id, apply)

    async def chunk(self, contract_id: str, owner_id: str, clauses: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """Chunk stored clauses, or supplied legacy clauses, without extending TTL."""
        chunks: list[dict[str, Any]] = []
        def apply(contract: dict[str, Any]) -> None:
            nonlocal chunks
            source = clauses if clauses is not None else contract["clauses"]
            if clauses is not None:
                contract["clauses"] = source
            chunks = ClauseChunker().chunk_clauses(contract_id, source)
            contract["chunks"] = chunks
            contract["embeddings"] = []
        await self.repository.update_contract(contract_id, owner_id, apply)
        return chunks

    async def embed(self, contract_id: str, owner_id: str, chunks: Sequence[dict[str, Any]] | None = None) -> int:
        """Embed chunks off the event loop and atomically retain results before expiry."""
        contract = await self.repository.get_contract(contract_id, owner_id)
        source = list(chunks) if chunks is not None else contract["chunks"]
        if not source:
            raise ValueError("Contract has no chunks to embed")
        async with self._embedding_gate():
            vectors = await asyncio.gather(*[asyncio.to_thread(self.embedding_service.embed_text, item["content"] if "content" in item else item["text"]) for item in source])
        embeddings = []
        for chunk, vector in zip(source, vectors):
            normalized = self._validate_vector(vector)
            embeddings.append({"chunk_id": chunk.get("chunk_id", str(chunk.get("chunk_index", len(embeddings)))), "chunk_index": chunk.get("chunk_index", len(embeddings)), "vector": normalized})
        def apply(updated: dict[str, Any]) -> None:
            if chunks is not None:
                updated["chunks"] = list(chunks)
            updated["embeddings"] = embeddings
        await self.repository.update_contract(contract_id, owner_id, apply)
        return len(embeddings)

    def _embedding_gate(self) -> asyncio.Semaphore:
        """Return the event-loop-local gate shared by all embedding requests."""
        loop = asyncio.get_running_loop()
        key = (id(loop), self.repository.settings.contract_processing_concurrency)
        semaphore = self._embedding_semaphores.get(key)
        if semaphore is None:
            semaphore = asyncio.Semaphore(self.repository.settings.contract_processing_concurrency)
            self._embedding_semaphores[key] = semaphore
        return semaphore

    async def search(self, contract_id: str, owner_id: str, query: str, top_k: int) -> list[dict[str, Any]]:
        """Search one contract's in-memory vectors using vectorized cosine similarity."""
        contract = await self.repository.get_contract(contract_id, owner_id)
        if not contract["embeddings"]:
            return []
        query_vector = await asyncio.to_thread(self.embedding_service.embed_text, query)
        return await asyncio.to_thread(self._rank, contract, query_vector, top_k)

    @staticmethod
    def _validate_vector(vector: Sequence[float]) -> list[float]:
        """Normalize and validate a single embedding vector."""
        array = np.asarray(vector, dtype=np.float32)
        if array.shape != (384,) or not np.isfinite(array).all() or float(np.linalg.norm(array)) == 0:
            raise InvalidEmbeddingError("Expected a finite non-zero 384-dimensional embedding")
        return array.tolist()

    @classmethod
    def _rank(cls, contract: dict[str, Any], query_vector: Sequence[float], top_k: int) -> list[dict[str, Any]]:
        """Return top matching chunks after validating query and stored vector shapes."""
        query = np.asarray(cls._validate_vector(query_vector), dtype=np.float32)
        rows = contract["embeddings"]
        matrix = np.asarray([row["vector"] for row in rows], dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[1] != 384 or not np.isfinite(matrix).all():
            raise InvalidEmbeddingError("Stored embeddings are invalid")
        norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(query)
        if np.any(norms == 0):
            raise InvalidEmbeddingError("Stored embeddings contain a zero vector")
        scores = matrix @ query / norms
        chunks = {str(chunk.get("chunk_id", chunk.get("chunk_index"))): chunk for chunk in contract["chunks"]}
        ordered = np.argsort(-scores)[:top_k]
        return [{"contract_id": contract["contract_id"], "chunk_id": rows[index]["chunk_id"], "content": chunks.get(str(rows[index]["chunk_id"]), {}).get("content", ""), "similarity": float(scores[index])} for index in ordered]
