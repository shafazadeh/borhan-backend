# src/contract_guard/application/use_cases/extract_closing.py

- extract_closing · function · L7-L23 — def extract_closing(text: str) -> tuple[str, str]: # Only consider final-document material; an incidental reference to signing # in a legal obligation must remain in the clause.
