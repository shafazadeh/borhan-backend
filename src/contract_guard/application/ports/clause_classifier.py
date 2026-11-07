from typing import Protocol
from contract_guard.domain.models.taxonomy import ClauseInput, Classification


class ClauseClassifier(Protocol):
    async def classify_batch(self, clauses: list[ClauseInput]) -> list[Classification]: ...
