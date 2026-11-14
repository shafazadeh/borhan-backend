# src/contract_guard/application/use_cases/normalize_clause_numbers.py

- _article_number · function · L15-L20 — def _article_number(title: str) -> int | None
- _record_correction · function · L23-L28 — def _record_correction(item: dict, after: str, old: str, new: str, corrections: list[dict]) -> None
- _correct_group · function · L31-L56 — def _correct_group(title: str, group: list[dict], candidates: dict, corrections: list[dict]) -> None
- _correct_references · function · L59-L71 — def _correct_references(clauses: list[dict], candidates: dict, known_articles: set[int], corrections: list[dict]) -> None
- normalize_clause_numbers · function · L74-L84 — def normalize_clause_numbers(clauses: list[dict]) -> list[dict]
