from dataclasses import dataclass
from .clause import Clause


@dataclass(frozen=True)
class Contract:
    clauses: tuple[Clause, ...]
