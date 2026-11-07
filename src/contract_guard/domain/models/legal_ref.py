from dataclasses import dataclass


@dataclass(frozen=True)
class LegalReference:
    source: str
    text: str
