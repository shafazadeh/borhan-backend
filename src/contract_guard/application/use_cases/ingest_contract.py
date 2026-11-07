from contract_guard.domain.models.clause import Clause
from contract_guard.domain.models.contract import Contract
from contract_guard.domain.ports.text_extractor import TextExtractor
from .clause_splitter import segment_clauses


def ingest_contract(data: bytes, extractor: TextExtractor) -> Contract:
    return Contract(tuple(Clause(**item) for item in segment_clauses(extractor.extract(data))))
