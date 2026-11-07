from typing import Protocol
from contract_guard.domain.models.legal_ref import LegalReference


class VectorStore(Protocol):
    def search(self, query: str, limit: int = 5) -> list[LegalReference]: ...
