import os
import hashlib
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from contract_guard.infrastructure.database.repositories.contract_repo import ContractRepository
from contract_guard.application.services.embedding import LocalEmbeddingService
from contract_guard.infrastructure.web.app import app
from fastapi.testclient import TestClient


def test_pgvector_ranking_and_owner_isolation():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated migrated PostgreSQL test database")

    owner, other = uuid4(), uuid4()
    with psycopg.connect(url, row_factory=dict_row) as connection:
        connection.execute("CREATE TEMP TABLE contract_embeddings (LIKE public.contract_embeddings INCLUDING DEFAULTS INCLUDING CONSTRAINTS) ON COMMIT DROP")
        connection.execute("CREATE UNIQUE INDEX ON contract_embeddings (user_id, contract_id, chunk_id)")

        @contextmanager
        def test_database():
            yield connection

        with patch("contract_guard.infrastructure.database.repositories.contract_repo.database", test_database):
            repository = ContractRepository()
            repository.save_chunk_embedding(owner, "test", "near", "پرداخت", [1.0, 0.0] + [0.0] * 382)
            repository.save_chunk_embedding(owner, "test", "middle", "قرارداد", [0.8, 0.6] + [0.0] * 382)
            repository.save_chunk_embedding(owner, "test", "far", "فسخ", [0.0, 1.0] + [0.0] * 382)
            repository.save_chunk_embedding(other, "private", "hidden", "محرمانه", [1.0, 0.0] + [0.0] * 382)
            results = repository.search_similar_chunks([1.0, 0.0] + [0.0] * 382, user_id=owner)
            assert [result["chunk_id"] for result in results] == ["near", "middle", "far"]
            assert results[0]["similarity"] > results[1]["similarity"] > results[2]["similarity"]
            assert repository.search_similar_chunks([1.0, 0.0] + [0.0] * 382, user_id=uuid4()) == []
        connection.rollback()


def test_real_persian_search_with_authenticated_user(monkeypatch):
    if os.getenv("RUN_REAL_EMBEDDING_TEST") != "1":
        pytest.skip("Set RUN_REAL_EMBEDDING_TEST=1 to load the real embedding model")
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated migrated PostgreSQL test database")
    with psycopg.connect(url) as connection:
        name = connection.execute("SELECT current_database()").fetchone()[0]
        if not name.startswith("contract_guard_search_test_"):
            pytest.fail("Real embedding test requires a dedicated contract_guard_search_test_ database")

    monkeypatch.setenv("DATABASE_URL", url)
    owner, other = uuid4(), uuid4()
    token = secrets.token_urlsafe(32)
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    try:
        with psycopg.connect(url) as connection:
            for user in (owner, other):
                connection.execute("INSERT INTO users (id, mobile_number) VALUES (%s, %s)", (user, user.hex[:20]))
            connection.execute(
                "INSERT INTO login_sessions (id, user_id, token_hash, expires_at, access_expires_at) VALUES (%s, %s, %s, %s, %s)",
                (uuid4(), owner, hashlib.sha256(token.encode()).hexdigest(), expiry, expiry),
            )
        repository, embedder = ContractRepository(), LocalEmbeddingService()
        chunks = [
            (owner, "payment", "مبلغ قرارداد در سه قسط ماهانه به حساب فروشنده پرداخت می‌شود."),
            (owner, "termination", "در صورت نقض تعهدات، طرف مقابل حق فسخ قرارداد دارد."),
            (owner, "delivery", "محل تحویل کالا انبار خریدار در تهران است."),
            (other, "private", "شرایط پرداخت و زمان پرداخت اقساط قرارداد محرمانه است."),
        ]
        for user, chunk_id, content in chunks:
            vector = embedder.embed_text(content)
            assert len(vector) == 384
            repository.save_chunk_embedding(user, "test-" + user.hex, chunk_id, content, vector)
        response = TestClient(app).post(
            "/api/v1/contracts/search",
            headers={"Authorization": "Bearer " + token},
            json={"query": "مبلغ قرارداد چگونه و چه زمانی پرداخت می‌شود؟", "top_k": 10},
        )
        assert response.status_code == 200, response.text
        results = response.json()
        print("Persian search ranking:", [(item["chunk_id"], round(item["similarity"], 4)) for item in results])
        assert [item["chunk_id"] for item in results][0] == "payment"
        assert {item["chunk_id"] for item in results} == {"payment", "termination", "delivery"}
        assert [item["similarity"] for item in results] == sorted((item["similarity"] for item in results), reverse=True)
    finally:
        with psycopg.connect(url) as connection:
            connection.execute("DELETE FROM users WHERE id IN (%s, %s)", (owner, other))
