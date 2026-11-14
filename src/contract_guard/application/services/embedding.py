from threading import Lock

from contract_guard.config.settings import Settings

_model = None
_model_lock = Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                settings = Settings()
                _model = SentenceTransformer(settings.embedding_model_name, revision=settings.embedding_model_revision)
    return _model


class LocalEmbeddingService:
    def embed_text(self, text: str) -> list[float]:
        return _get_model().encode(text, convert_to_numpy=True).tolist()
