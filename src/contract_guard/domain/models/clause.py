from dataclasses import dataclass


@dataclass(frozen=True)
class Clause:
    clause_id: str
    index: int
    text: str
    article_title: str = ""
    original_text: str | None = None
