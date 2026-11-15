"""Contract-based temporary storage endpoints."""

import asyncio
import logging
import secrets
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from contract_guard.application.services.temporary_contracts import ContractPayloadTooLargeError, ContractProcessingExpiredError, InvalidEmbeddingError, TemporaryContractService
from contract_guard.application.use_cases.classify_clauses import HybridClauseClassifier
from contract_guard.config.settings import Settings
from contract_guard.domain.models.taxonomy import ClauseInput
from contract_guard.infrastructure.cache.contract_repository import ContractCapacityError, ContractNotFoundError, ContractStorageError, TemporaryContractRepository
from contract_guard.infrastructure.llm.taxonomy_gateway import LLMTaxonomyGateway
from contract_guard.infrastructure.web.dependencies import current_session
from contract_guard.infrastructure.web.v1.endpoints.ingestion import read_contract_upload

router = APIRouter()
logger = logging.getLogger(__name__)


class SearchContractRequest(BaseModel):
    """Validate a contract-scoped semantic search request."""
    query: str = Field(min_length=1, max_length=10_000)
    top_k: int = Field(default=5, ge=1, le=100)


def _service() -> TemporaryContractService:
    """Build the current request's temporary-contract application service."""
    return TemporaryContractService(TemporaryContractRepository())


def _raise_storage_error(exc: Exception) -> None:
    """Map storage failures to stable public HTTP responses without logging data."""
    if isinstance(exc, ContractNotFoundError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contract not found") from exc
    if isinstance(exc, ContractCapacityError):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Temporary contract capacity reached") from exc
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Temporary contract storage is unavailable") from exc


@router.post("/contracts", status_code=status.HTTP_201_CREATED, tags=["contracts"])
async def create_contract(request: Request, user=Depends(current_session)):
    """Extract a PDF/DOCX and retain its data only in the dedicated Redis instance."""
    try:
        extracted = await read_contract_upload(request, Settings().contract_max_payload_bytes)
        service = _service()
        contract = await service.create(secrets.token_urlsafe(24), str(user["id"]), extracted)
        return {"contract_id": contract["contract_id"], "expires_in": Settings().contract_ttl_seconds, "expires_at": contract["expires_at"]}
    except ContractPayloadTooLargeError as exc:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Contract exceeds the temporary-storage limit") from exc
    except (ContractStorageError, ContractNotFoundError) as exc:
        _raise_storage_error(exc)


@router.get("/contracts/{contract_id}", tags=["contracts"])
async def get_contract(contract_id: str, user=Depends(current_session)):
    """Return an owner-scoped temporary contract and its remaining lifetime."""
    try:
        service = _service()
        contract = await service.repository.get_contract(contract_id, str(user["id"]))
        contract["expires_in"] = await service.repository.get_contract_ttl(contract_id, str(user["id"]))
        return contract
    except (ContractStorageError, ContractNotFoundError) as exc:
        _raise_storage_error(exc)


@router.delete("/contracts/{contract_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["contracts"])
async def delete_contract(contract_id: str, user=Depends(current_session)):
    """Immediately remove an owner-scoped temporary contract."""
    try:
        await _service().repository.delete_contract(contract_id, str(user["id"]))
    except (ContractStorageError, ContractNotFoundError) as exc:
        _raise_storage_error(exc)


@router.post("/contracts/{contract_id}/classify", tags=["contracts"])
async def classify_stored_contract(contract_id: str, user=Depends(current_session)):
    """Classify stored clauses and retain results only before the original deadline."""
    service = _service()
    try:
        contract = await service.repository.get_contract(contract_id, str(user["id"]))
        clauses = [ClauseInput.model_validate({key: item[key] for key in ("clause_id", "index", "article_title", "text")}) for item in contract["clauses"]]
        classifications = await HybridClauseClassifier(LLMTaxonomyGateway(), Settings().taxonomy_llm_concurrency).classify_batch(clauses)
        await service.classify(contract_id, str(user["id"]), [item.model_dump(mode="json") for item in classifications])
        return classifications
    except (ContractStorageError, ContractNotFoundError) as exc:
        _raise_storage_error(exc)


@router.post("/contracts/{contract_id}/chunk", tags=["contracts"])
async def chunk_stored_contract(contract_id: str, user=Depends(current_session)):
    """Chunk the stored clauses and replace only derived volatile fields."""
    try:
        return await _service().chunk(contract_id, str(user["id"]))
    except ContractPayloadTooLargeError as exc:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Contract exceeds the temporary-storage limit") from exc
    except (ContractStorageError, ContractNotFoundError) as exc:
        _raise_storage_error(exc)


@router.post("/contracts/{contract_id}/embed", tags=["contracts"])
async def embed_stored_contract(contract_id: str, user=Depends(current_session)):
    """Generate embeddings without blocking the event loop or extending TTL."""
    try:
        count = await _service().embed(contract_id, str(user["id"]))
        return {"status": "saved", "dimension": 384, "count": count}
    except (ContractStorageError, ContractNotFoundError) as exc:
        _raise_storage_error(exc)
    except ContractProcessingExpiredError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contract not found") from exc
    except (ValueError, InvalidEmbeddingError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.post("/contracts/{contract_id}/search", tags=["contracts"])
async def search_stored_contract(contract_id: str, body: SearchContractRequest, user=Depends(current_session)):
    """Search embeddings belonging solely to the selected temporary contract."""
    try:
        return await _service().search(contract_id, str(user["id"]), body.query.strip(), body.top_k)
    except (ContractStorageError, ContractNotFoundError) as exc:
        _raise_storage_error(exc)
    except ContractProcessingExpiredError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contract not found") from exc
    except InvalidEmbeddingError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
