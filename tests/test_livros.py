from unittest.mock import patch
from fastapi.testclient import TestClient
from livros import app

client = TestClient(app)

@patch('livros.redis_client')
def test_ver_livros_vazio(mock_redis):
    mock_redis.keys.return_value = []

    resposta = client.get("/debug/redis")
    
    assert resposta.status_code == 200
    assert resposta.json() == []
