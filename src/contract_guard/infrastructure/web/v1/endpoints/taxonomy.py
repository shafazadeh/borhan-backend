from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from contract_guard.application.use_cases.classify_clauses import HybridClauseClassifier
from contract_guard.config.settings import Settings
from contract_guard.domain.models.taxonomy import ClauseInput, Classification
from contract_guard.infrastructure.llm.taxonomy_gateway import LLMTaxonomyGateway
from contract_guard.infrastructure.web.dependencies import current_session

router = APIRouter()


class ClassifyRequest(BaseModel):
    clauses: list[ClauseInput] = Field(max_length=500)


@router.post("/contracts/classify", response_model=list[Classification])
async def classify_contract(body: ClassifyRequest, user=Depends(current_session)):
    return await HybridClauseClassifier(LLMTaxonomyGateway(), Settings().taxonomy_llm_concurrency).classify_batch(body.clauses)
