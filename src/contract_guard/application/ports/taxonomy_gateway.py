from typing import Protocol
from contract_guard.domain.models.taxonomy import ClauseInput, Classification


class TaxonomyGateway(Protocol):
    async def classify(self, clause: ClauseInput) -> Classification: ...
