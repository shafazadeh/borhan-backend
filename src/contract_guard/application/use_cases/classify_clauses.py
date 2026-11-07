import asyncio
from contract_guard.application.ports.taxonomy_gateway import TaxonomyGateway
from contract_guard.application.use_cases.taxonomy_rules import classify_rule
from contract_guard.domain.models.taxonomy import Category, ClauseInput, Classification, ClassificationSource


class HybridClauseClassifier:
    def __init__(self, gateway: TaxonomyGateway, concurrency: int):
        self.gateway = gateway
        self.semaphore = asyncio.Semaphore(concurrency)

    async def classify_batch(self, clauses: list[ClauseInput]) -> list[Classification]:
        async def classify(clause):
            result = classify_rule(clause)
            if result is not None:
                return result
            try:
                async with self.semaphore:
                    return await self.gateway.classify(clause)
            except Exception:
                return Classification(clause_id=clause.clause_id, primary_category=Category.general_legal,
                    secondary_categories=[], confidence=0.0, matched_keywords=[], source=ClassificationSource.llm, degraded=True)
        return list(await asyncio.gather(*(classify(clause) for clause in clauses)))
