from typing import Protocol
from uuid import UUID

from contract_guard.domain.services.embedding import EmbeddingService


class ChunkSearchRepository(Protocol):
    def search_similar_chunks(self, query_embedding: list[float], limit: int = 5, *, user_id: UUID) -> list[dict]: ...


class SemanticSearchService:
    def __init__(self, embedding_service: EmbeddingService, repository: ChunkSearchRepository):
        self.embedding_service = embedding_service
        self.repository = repository

    def search(self, query: str, user_id: UUID, limit: int = 5) -> list[dict]:
        vector = self.embedding_service.embed_text(query)
        if len(vector) != 384:
            raise EmbeddingDimensionError(f"Expected 384 embedding dimensions, got {len(vector)}")
        return self.repository.search_similar_chunks(vector, limit, user_id=user_id)


class EmbeddingDimensionError(ValueError):
    pass
