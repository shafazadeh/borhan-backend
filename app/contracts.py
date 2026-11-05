import asyncio
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.auth import current_user
from app.services.analysis import analyze_clauses
from app.services.clauses import segment_clauses
from app.services.documents import extract_document
from app.services.risk_classifier import ModelServiceError, ModelServiceTimeout
from app.services.sessions import SessionStore
from app.services.uploads import read_upload


router = APIRouter(prefix="/api/v1/contracts", tags=["contracts"])
NOT_FOUND = "جلسه بررسی منقضی شده و به دلایل امنیتی داده‌ها منهدم شده‌اند. لطفاً فایل را مجدداً آپلود فرمایید."


class ClauseResult(BaseModel):
    clause_id: UUID
    index: int
    text: str
    type: Literal["informational", "risk_analysis"] = "risk_analysis"
    skip_reason: Literal["short_text", "identification", "empty_heading", "preamble"] | None = None
    result: str | None


class ContractSession(BaseModel):
    contract_id: UUID
    created_at: datetime
    expires_in_seconds: int
    total_clauses: int
    clauses: list[ClauseResult]


@router.post("/upload", response_model=ContractSession, openapi_extra={"requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {"type": "object", "required": ["file"], "properties": {"file": {"type": "string", "format": "binary"}}}}}}})
async def upload_contract(request: Request, user_id: str = Depends(current_user)):
    data, content_type = await read_upload(request)
    text = await asyncio.to_thread(extract_document, data, content_type)
    del data
    clauses = segment_clauses(text)
    del text
    if not clauses:
        raise HTTPException(status_code=422, detail="Unable to extract document")
    try:
        analyzed = await analyze_clauses(clauses, request.app.state.model_semaphore)
    except ModelServiceTimeout:
        raise HTTPException(status_code=504, detail="Model service timed out") from None
    except ModelServiceError:
        raise HTTPException(status_code=502, detail="Model service failed") from None
    session = {
        "contract_id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_clauses": len(analyzed),
        "clauses": analyzed,
    }
    store = SessionStore(request.app.state.settings.redis_url)
    await asyncio.to_thread(store.save, user_id, session)
    session["expires_in_seconds"] = 7200
    return session


@router.get("/{contract_id}", response_model=ContractSession)
def get_contract(contract_id: UUID, request: Request, user_id: str = Depends(current_user)):
    session = SessionStore(request.app.state.settings.redis_url).get(user_id, str(contract_id))
    if session is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return session


@router.delete("/{contract_id}", status_code=204)
def delete_contract(contract_id: UUID, request: Request, user_id: str = Depends(current_user)):
    if not SessionStore(request.app.state.settings.redis_url).delete(user_id, str(contract_id)):
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return Response(status_code=204)
