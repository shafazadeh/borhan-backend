from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from contract_guard.application.services.chunking import ClauseChunker
from contract_guard.infrastructure.web.dependencies import current_session

router = APIRouter()


class ClauseForChunking(BaseModel):
    text: str = Field(min_length=1, max_length=100000)
    clause_category: str | None = Field(default=None, max_length=50)
    clause_id: str | None = None
    index: int | None = None
    article_title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkRequest(BaseModel):
    contract_id: str = Field(min_length=1, max_length=100)
    clauses: list[ClauseForChunking] = Field(max_length=500)


class ClauseChunk(BaseModel):
    contract_id: str
    clause_category: str | None
    chunk_index: int
    content: str
    metadata: dict[str, Any]


@router.post("/contracts/chunk", response_model=list[ClauseChunk], tags=["contracts"])
def chunk_contract(body: ChunkRequest, user=Depends(current_session)):
    return ClauseChunker().chunk_clauses(
        body.contract_id, [clause.model_dump(exclude_none=True) for clause in body.clauses]
    )
