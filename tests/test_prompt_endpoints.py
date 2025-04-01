import pytest
from fastapi.testclient import TestClient
from datetime import datetime

def test_execute_prompt(test_client: TestClient, sample_prompt_request):
    response = test_client.post("/api/v1/prompts/execute", json=sample_prompt_request)
    assert response.status_code == 200
    data = response.json()
    assert "response_text" in data
    assert "execution_time" in data
    assert "model_used" in data
    assert data["model_used"] == sample_prompt_request["model"]

def test_execute_prompt_invalid_request(test_client: TestClient):
    response = test_client.post("/api/v1/prompts/execute", json={})
    assert response.status_code == 422

def test_start_cycle(test_client: TestClient, sample_cycle_request):
    response = test_client.post("/api/v1/prompts/cycle", json=sample_cycle_request)
    assert response.status_code == 200
    data = response.json()
    assert "response_text" in data
    assert "execution_time" in data
    assert "model_used" in data

def test_start_cycle_invalid_request(test_client: TestClient):
    response = test_client.post("/api/v1/prompts/cycle", json={})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_prompt_service_execute(mock_prompt_service, sample_prompt_request):
    from app.schemas.prompt_schema import PromptRequest
    
    request = PromptRequest(**sample_prompt_request)
    mock_prompt_service.dreamscape.execute_prompt.return_value.text = "Test response"
    
    response = await mock_prompt_service.execute_prompt(request)
    assert response.response_text == "Test response"
    assert response.model_used == sample_prompt_request["model"]
    assert isinstance(response.execution_time, float) 
