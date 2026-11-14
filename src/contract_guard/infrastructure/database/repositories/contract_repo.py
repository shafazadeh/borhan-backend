import json

from contract_guard.infrastructure.database.session import database


class ContractRepository:
    def save_chunk_embedding(self, user_id, contract_id: str, chunk_id: str,
                             text: str, embedding: list[float]) -> None:
        if len(embedding) != 384:
            raise ValueError("Expected a 384-dimensional embedding")
        with database() as connection:
            connection.execute(
                """INSERT INTO contract_embeddings
                   (user_id, contract_id, chunk_id, chunk_index, content, embedding)
                   VALUES (%s, %s, %s, 0, %s, %s::vector)
                   ON CONFLICT (user_id, contract_id, chunk_id)
                   DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding""",
                (user_id, contract_id, chunk_id, text, json.dumps(embedding, allow_nan=False)),
            )

    def search_similar_chunks(self, query_embedding: list[float], limit: int = 5, *, user_id) -> list[dict]:
        if len(query_embedding) != 384:
            raise ValueError("Expected a 384-dimensional embedding")
        if limit < 1:
            raise ValueError("Limit must be positive")
        vector = json.dumps(query_embedding, allow_nan=False)
        with database() as connection:
            return connection.execute(
                """SELECT contract_id, chunk_id, content,
                          1 - (embedding <=> %s::vector) AS similarity
                   FROM contract_embeddings
                   WHERE user_id = %s AND embedding IS NOT NULL
                   ORDER BY (embedding <=> %s::vector) + 0
                   LIMIT %s""",
                (vector, user_id, vector, limit),
            ).fetchall()
