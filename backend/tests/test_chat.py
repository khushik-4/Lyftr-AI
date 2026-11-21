from unittest.mock import patch
from tests.conftest import make_mock_response


def test_validation_missing_session_id(client):
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 422
    assert "detail" in response.json()


def test_validation_empty_message(client):
    response = client.post("/chat", json={"session_id": "sess-1", "message": ""})
    assert response.status_code == 422
    assert "detail" in response.json()


def test_validation_whitespace_only_message(client):
    response = client.post("/chat", json={"session_id": "sess-1", "message": "    \n\t  "})
    assert response.status_code == 422
    assert "detail" in response.json()


def test_validation_message_too_long(client):
    long_message = "a" * 4001
    response = client.post("/chat", json={"session_id": "sess-1", "message": long_message})
    assert response.status_code == 422
    assert "detail" in response.json()


@patch("litellm.completion")
def test_valid_chat_success(mock_completion, client):
    mock_completion.return_value = make_mock_response("Hello from AI!", prompt_tokens=20, completion_tokens=5)

    response = client.post("/chat", json={
        "session_id": "sess-valid-1",
        "message": "Hello there!"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "sess-valid-1"
    assert data["reply"] == "Hello from AI!"
    metadata = data["metadata"]
    assert metadata["resolution_source"] == "LIVE_INFERENCE"
    assert metadata["model"] == "gemini/gemini-2.0-flash"
    assert metadata["input_tokens"] == 20
    assert metadata["output_tokens"] == 5
    assert metadata["key_id"] == "key_1"
    assert metadata["fallback_attempts"] == 0
    assert isinstance(metadata["latency_ms"], int)
