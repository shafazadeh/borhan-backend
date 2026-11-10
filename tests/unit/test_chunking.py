from fastapi.testclient import TestClient

from contract_guard.application.services.chunking import ClauseChunker
from contract_guard.infrastructure.web.app import app
from contract_guard.infrastructure.web.dependencies import current_session


def test_short_clauses_preserve_text_and_context():
    clauses = [{"text": "  بند کوتاه.  ", "clause_id": "1", "clause_category": "financial",
                "metadata": {"page": 2}}, {"text": "x" * 800}]
    chunks = ClauseChunker().chunk_clauses("contract-1", clauses)
    assert [chunk["content"] for chunk in chunks] == [clauses[0]["text"], clauses[1]["text"]]
    assert chunks[0] == {"contract_id": "contract-1", "clause_category": "financial",
                         "chunk_index": 0, "content": clauses[0]["text"],
                         "metadata": {"page": 2, "clause_id": "1"}}
    assert chunks[1]["chunk_index"] == 1


def test_long_clauses_overlap_without_losing_text():
    for text in ("عبارت قراردادی " * 150, "x" * 2000, "a" * 800 + " "):
        chunks = ClauseChunker().chunk_clauses("contract-1", [{"text": text}])
        parts = [chunk["content"] for chunk in chunks]
        assert len(parts) > 1
        assert all(len(part) <= 800 for part in parts)
        assert all(left[-150:] == right[:150] for left, right in zip(parts, parts[1:]))
        assert parts[0] + "".join(part[150:] for part in parts[1:]) == text
        assert [chunk["chunk_index"] for chunk in chunks] == list(range(len(chunks)))


def test_chunk_endpoint():
    app.dependency_overrides[current_session] = lambda: {"id": "test-user"}
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/contracts/chunk", json={
                "contract_id": "contract-1",
                "clauses": [{"text": "پرداخت ظرف ده روز انجام می‌شود.", "clause_category": "financial"}],
            })
        assert response.status_code == 200
        assert response.json() == [{"contract_id": "contract-1", "clause_category": "financial",
                                    "chunk_index": 0, "content": "پرداخت ظرف ده روز انجام می‌شود.",
                                    "metadata": {}}]
    finally:
        app.dependency_overrides.pop(current_session, None)
