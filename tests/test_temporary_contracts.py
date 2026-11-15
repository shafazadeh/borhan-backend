"""Unit tests for volatile contract processing without PostgreSQL."""

import asyncio
from copy import deepcopy

import pytest

from contract_guard.application.services.temporary_contracts import InvalidEmbeddingError, TemporaryContractService
from contract_guard.infrastructure.cache.contract_repository import ContractNotFoundError


class Settings:
    """Small settings substitute for in-memory service tests."""
    contract_ttl_seconds = 60
    contract_processing_concurrency = 1


class Repository:
    """In-memory repository double that records owner-scoped writes."""
    def __init__(self):
        self.settings = Settings()
        self.contracts = {}

    async def create_contract(self, contract):
        """Store a test contract."""
        self.contracts[contract["contract_id"]] = deepcopy(contract)

    async def get_contract(self, contract_id, owner_id):
        """Return only an owner's contract."""
        contract = self.contracts.get(contract_id)
        if contract is None or contract["owner_id"] != owner_id:
            raise ContractNotFoundError()
        return deepcopy(contract)

    async def update_contract(self, contract_id, owner_id, update):
        """Apply an update without tracking a TTL refresh."""
        contract = await self.get_contract(contract_id, owner_id)
        update(contract)
        self.contracts[contract_id] = contract
        return deepcopy(contract)


class Embedder:
    """Deterministic 384-dimensional embedding double."""
    def embed_text(self, text):
        """Encode matching strings on orthogonal test dimensions."""
        vector = [0.0] * 384
        vector[0 if text == "payment" else 1] = 1.0
        return vector


def test_contract_search_is_scoped_to_the_selected_contract():
    """Search must return chunks from only the requested contract."""
    async def scenario():
        repository = Repository()
        service = TemporaryContractService(repository, Embedder())
        await service.create("one", "owner", {"text": "a", "clauses": [], "closing_metadata": {}})
        await service.create("two", "owner", {"text": "b", "clauses": [], "closing_metadata": {}})
        await service.embed("one", "owner", [{"chunk_id": "a", "content": "payment"}])
        await service.embed("two", "owner", [{"chunk_id": "b", "content": "other"}])
        return await service.search("one", "owner", "payment", 5)
    assert asyncio.run(scenario()) == [{"contract_id": "one", "chunk_id": "a", "content": "payment", "similarity": 1.0}]


def test_other_owner_cannot_read_or_update_contract():
    """Owner isolation applies before embedding work starts."""
    async def scenario():
        repository = Repository()
        service = TemporaryContractService(repository, Embedder())
        await service.create("one", "owner", {"text": "a", "clauses": [], "closing_metadata": {}})
        await service.embed("one", "other", [{"chunk_id": "a", "content": "payment"}])
    with pytest.raises(ContractNotFoundError):
        asyncio.run(scenario())


def test_invalid_embedding_dimension_is_rejected():
    """Vector validation rejects vectors that cannot support cosine ranking."""
    with pytest.raises(InvalidEmbeddingError):
        TemporaryContractService._validate_vector([1.0, 2.0])
