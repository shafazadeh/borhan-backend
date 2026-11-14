import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from contract_guard.application.services.embedding import LocalEmbeddingService
from contract_guard.application.services.semantic_search import EmbeddingDimensionError, SemanticSearchService
from contract_guard.infrastructure.database.repositories.contract_repo import ContractRepository
from contract_guard.infrastructure.web.dependencies import current_session

router = APIRouter()
logger = logging.getLogger(__name__)


class EmbedChunkRequest(BaseModel):
    contract_id: str = Field(min_length=1, max_length=100)
    chunk_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=100000)


class EmbedChunkResponse(BaseModel):
    status: str
    dimension: int


@router.post("/contracts/embed-chunk", response_model=EmbedChunkResponse, tags=["contracts"])
def embed_chunk(body: EmbedChunkRequest, user=Depends(current_session)):
    vector = LocalEmbeddingService().embed_text(body.text)
    ContractRepository().save_chunk_embedding(user["id"], body.contract_id, body.chunk_id, body.text, vector)
    return EmbedChunkResponse(status="saved", dimension=len(vector))


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [{"query": "شرایط پرداخت قرارداد چیست؟", "top_k": 5}]})

    query: str = Field(min_length=1, max_length=10000, description="متن پرس‌وجوی معنایی")
    top_k: int = Field(default=5, ge=1, le=100, validation_alias=AliasChoices("top_k", "limit"), description="حداکثر تعداد نتایج، بین ۱ تا ۱۰۰")

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("متن پرس‌وجو نمی‌تواند خالی باشد")
        return value


class SimilarChunkResponse(BaseModel):
    contract_id: str = Field(description="شناسه قرارداد")
    chunk_id: str | None = Field(description="شناسه چانک؛ برای داده‌های قدیمی ممکن است خالی باشد")
    content: str = Field(description="متن چانک")
    similarity: float = Field(description="شباهت کسینوسی؛ احتمال نیست و مقدار بیشتر به معنای شباهت بیشتر است")


@router.post(
    "/contracts/search", response_model=list[SimilarChunkResponse], tags=["contracts"],
    summary="جستجوی معنایی چانک‌های قرارداد",
    description="چانک‌های متعلق به کاربر جاری را با شباهت کسینوسی و به ترتیب بیشترین شباهت برمی‌گرداند. توکن Bearer لازم است.",
    responses={
        200: {"description": "نتایج مرتب‌شده؛ در صورت نبود نتیجه فهرست خالی است", "content": {"application/json": {"example": [{"contract_id": "contract-1", "chunk_id": "chunk-1", "content": "پرداخت اقساط طبق توافق انجام می‌شود.", "similarity": 0.82}]}}},
        401: {"description": "توکن نامعتبر یا ارائه نشده است"},
        422: {"description": "ورودی نامعتبر است"},
        500: {"description": "ابعاد بردار مدل با ابعاد مورد انتظار سازگار نیست"},
        503: {"description": "سرویس مدل یا پایگاه داده در دسترس نیست"},
    },
)
def search_chunks(body: SearchRequest, user=Depends(current_session)):
    service = SemanticSearchService(LocalEmbeddingService(), ContractRepository())
    try:
        return service.search(body.query, user["id"], body.top_k)
    except EmbeddingDimensionError:
        logger.exception("Search embedding dimension mismatch")
        raise HTTPException(500, "ابعاد بردار مدل با مقدار مورد انتظار ۳۸۴ سازگار نیست") from None
    except Exception:
        logger.exception("Semantic search dependency failed")
        raise HTTPException(503, "سرویس جستجو موقتاً در دسترس نیست") from None
