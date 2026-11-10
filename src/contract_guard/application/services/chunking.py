class ClauseChunker:
    """Split clauses into bounded chunks while retaining their context."""

    chunk_size = 800
    overlap = 150

    def chunk_clauses(self, contract_id: str, clauses: list[dict]) -> list[dict]:
        chunks = []
        for clause in clauses:
            text = clause["text"]
            metadata = dict(clause.get("metadata") or {})
            for key in ("clause_id", "index", "article_title"):
                if key in clause:
                    metadata[key] = clause[key]

            start = 0
            while True:
                end = min(start + self.chunk_size, len(text))
                if end < len(text):
                    # Prefer a word boundary in the latter half of the window.
                    boundary = max((i + 1 for i in range(start + self.chunk_size // 2, end)
                                    if text[i].isspace()), default=end)
                    end = boundary
                chunks.append({
                    "contract_id": contract_id,
                    "clause_category": clause.get("clause_category"),
                    "chunk_index": len(chunks),
                    "content": text[start:end],
                    "metadata": metadata.copy(),
                })
                if end == len(text):
                    break
                start = end - self.overlap
        return chunks
