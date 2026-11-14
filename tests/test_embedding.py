from unittest.mock import patch

from fastapi.testclient import TestClient

from contract_guard.application.services import embedding
from contract_guard.infrastructure.web.app import app
from contract_guard.infrastructure.web.dependencies import current_session


def test_embedding_model_is_reused():
    class Model:
        def encode(self, text, **kwargs):
            class Vector:
                def tolist(self):
                    return [0.5] * 384
            return Vector()

    with patch.object(embedding, '_model', Model()):
        assert len(embedding.LocalEmbeddingService().embed_text('متن قرارداد')) == 384
        assert embedding._get_model() is embedding._get_model()


def test_embed_endpoint_saves_and_reports_dimension():
    app.dependency_overrides[current_session] = lambda: {'id': 'user-id'}
    try:
        with patch('contract_guard.infrastructure.web.v1.endpoints.embedding.LocalEmbeddingService.embed_text', return_value=[0.1] * 384), patch('contract_guard.infrastructure.web.v1.endpoints.embedding.ContractRepository.save_chunk_embedding') as save:
            response = TestClient(app).post('/api/v1/contracts/embed-chunk', json={'contract_id': 'contract-1', 'chunk_id': 'chunk-1', 'text': 'متن قرارداد'})
        assert response.status_code == 200
        assert response.json() == {'status': 'saved', 'dimension': 384}
        assert save.call_args.args[:4] == ('user-id', 'contract-1', 'chunk-1', 'متن قرارداد')
        assert len(save.call_args.args[4]) == 384
    finally:
        app.dependency_overrides.clear()


def test_embed_endpoint_requires_authentication():
    response = TestClient(app).post('/api/v1/contracts/embed-chunk', json={'contract_id': '1', 'chunk_id': '1', 'text': 'text'})
    assert response.status_code == 401
