from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from contract_guard.application.services.semantic_search import EmbeddingDimensionError, SemanticSearchService
from contract_guard.infrastructure.database.repositories.contract_repo import ContractRepository
from contract_guard.infrastructure.web.app import app
from contract_guard.infrastructure.web.dependencies import current_session


def test_search_embeds_query_and_scopes_repository_to_user():
    embedder = Mock()
    embedder.embed_text.return_value = [0.1] * 384
    repository = Mock()
    repository.search_similar_chunks.return_value = [{"content": "contract text"}]

    result = SemanticSearchService(embedder, repository).search("payment", "user-1", 3)

    assert result == [{"content": "contract text"}]
    embedder.embed_text.assert_called_once_with("payment")
    repository.search_similar_chunks.assert_called_once_with([0.1] * 384, 3, user_id="user-1")


def test_repository_filters_by_owner_and_orders_by_cosine_distance():
    connection = Mock()
    connection.execute.return_value.fetchall.return_value = [{"content": "text", "similarity": 0.9}]

    @contextmanager
    def fake_database():
        yield connection

    with patch("contract_guard.infrastructure.database.repositories.contract_repo.database", fake_database):
        result = ContractRepository().search_similar_chunks([0.1] * 384, user_id="user-1")

    query, parameters = connection.execute.call_args.args
    assert "WHERE user_id = %s" in query
    assert "ORDER BY (embedding <=> %s::vector) + 0" in query
    assert parameters[1] == "user-1"
    assert parameters[-1] == 5
    assert result[0]["similarity"] == 0.9


def test_search_endpoint_returns_results_and_validates_limit():
    app.dependency_overrides[current_session] = lambda: {"id": "user-1"}
    try:
        with patch("contract_guard.infrastructure.web.v1.endpoints.embedding.SemanticSearchService.search") as search:
            search.return_value = [{"contract_id": "contract-1", "chunk_id": "chunk-1", "content": "text", "similarity": 0.9}]
            client = TestClient(app)
            response = client.post("/api/v1/contracts/search", json={"query": "payment"})
            assert response.status_code == 200
            assert response.json() == search.return_value
            search.assert_called_once_with("payment", "user-1", 5)
            assert client.post("/api/v1/contracts/search", json={"query": "payment", "limit": 0}).status_code == 422
    finally:
        app.dependency_overrides.pop(current_session, None)


def test_search_endpoint_requires_authentication():
    response = TestClient(app).post("/api/v1/contracts/search", json={"query": "payment"})
    assert response.status_code == 401


def test_dimension_mismatch_does_not_query_database():
    embedder = Mock()
    embedder.embed_text.return_value = [0.1] * 3
    repository = Mock()
    with pytest.raises(EmbeddingDimensionError, match="384.*3"):
        SemanticSearchService(embedder, repository).search("پرداخت", "user-1")
    repository.search_similar_chunks.assert_not_called()


def test_search_validation_empty_results_and_openapi():
    app.dependency_overrides[current_session] = lambda: {"id": "user-1"}
    try:
        client = TestClient(app)
        with patch("contract_guard.infrastructure.web.v1.endpoints.embedding.SemanticSearchService.search", return_value=[]) as search:
            assert client.post("/api/v1/contracts/search", json={"query": "  "}).status_code == 422
            assert client.post("/api/v1/contracts/search", json={"query": "پرداخت", "top_k": 101}).status_code == 422
            response = client.post("/api/v1/contracts/search", json={"query": " پرداخت ", "top_k": 2})
            assert response.status_code == 200 and response.json() == []
            search.assert_called_once_with("پرداخت", "user-1", 2)
        operation = client.get("/openapi.json").json()["paths"]["/api/v1/contracts/search"]["post"]
        assert operation["security"] and "503" in operation["responses"]
        assert client.get("/docs").status_code == 200
    finally:
        app.dependency_overrides.pop(current_session, None)


@pytest.mark.parametrize("error,status", [(EmbeddingDimensionError("wrong dimensions"), 500), (RuntimeError("private details"), 503)])
def test_search_dependency_errors_are_sanitized(error, status):
    app.dependency_overrides[current_session] = lambda: {"id": "user-1"}
    try:
        with patch("contract_guard.infrastructure.web.v1.endpoints.embedding.SemanticSearchService.search", side_effect=error):
            response = TestClient(app).post("/api/v1/contracts/search", json={"query": "پرداخت"})
        assert response.status_code == status
        assert "private details" not in response.text
    finally:
        app.dependency_overrides.pop(current_session, None)
