from typing import Protocol


class EmbeddingService(Protocol):
    def embed_text(self, text: str) -> list[float]: ...
