"""Legacy contract embedding routes backed exclusively by temporary Redis storage."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from contract_guard.application.services.temporary_contracts import InvalidEmbeddingError, TemporaryContractService
from contract_guard.infrastructure.cache.contract_repository import ContractNotFoundError, ContractStorageError, TemporaryContractRepository
from contract_guard.infrastructure.web.dependencies import current_session

router = APIRouter()


class EmbedChunkRequest(BaseModel):
    """Validate an explicitly supplied chunk for a temporary contract."""
    contract_id: str = Field(min_length=1, max_length=100)
    chunk_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=100000)


class EmbedChunkResponse(BaseModel):
    """Describe a successful volatile embedding write."""
    status: str
    dimension: int


class SearchRequest(BaseModel):
    """Validate the breaking, contract-scoped legacy search API."""
    model_config = ConfigDict(extra="forbid")
    contract_id: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=1, max_length=10000)
    top_k: int = Field(default=5, ge=1, le=100, validation_alias=AliasChoices("top_k", "limit"))

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """Reject whitespace-only search queries."""
        value = value.strip()
        if not value:
            raise ValueError("Query cannot be empty")
        return value


class SimilarChunkResponse(BaseModel):
    """Represent a semantic-search match from the selected contract."""
    contract_id: str
    chunk_id: str | None
    content: str
    similarity: float


def _service() -> TemporaryContractService:
    """Create the shared temporary-contract application service."""
    return TemporaryContractService(TemporaryContractRepository())


def _storage_http_error(exc: Exception) -> HTTPException:
    """Translate repository exceptions without exposing infrastructure details."""
    if isinstance(exc, ContractNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Contract not found")
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Temporary contract storage is unavailable")


@router.post("/contracts/embed-chunk", response_model=EmbedChunkResponse, tags=["contracts"])
async def embed_chunk(body: EmbedChunkRequest, user=Depends(current_session)):
    """Embed one supplied chunk after validating the selected contract's ownership."""
    try:
        await _service().embed(body.contract_id, str(user["id"]), [{"chunk_id": body.chunk_id, "chunk_index": 0, "content": body.text}])
        return EmbedChunkResponse(status="saved", dimension=384)
    except (ContractStorageError, ContractNotFoundError) as exc:
        raise _storage_http_error(exc) from exc
    except (ValueError, InvalidEmbeddingError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.post("/contracts/search", response_model=list[SimilarChunkResponse], tags=["contracts"])
async def search_chunks(body: SearchRequest, user=Depends(current_session)):
    """Search only the selected temporary contract; PostgreSQL is never consulted."""
    try:
        return await _service().search(body.contract_id, str(user["id"]), body.query, body.top_k)
    except (ContractStorageError, ContractNotFoundError) as exc:
        raise _storage_http_error(exc) from exc
    except InvalidEmbeddingError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
