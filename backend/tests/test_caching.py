from unittest.mock import patch
from tests.conftest import make_mock_response


@patch("litellm.completion")
def test_caching_behavior(mock_completion, client):
    # Only one mock response should be consumed from litellm.completion
    mock_completion.return_value = make_mock_response(
        "Paris is the capital of France.",
        prompt_tokens=42,
        completion_tokens=9
    )

    # 1. First session asks question -> LIVE_INFERENCE
    resp1 = client.post("/chat", json={
        "session_id": "session-france-1",
        "message": "What is the capital of France?"
    })

    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["reply"] == "Paris is the capital of France."
    assert data1["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert data1["metadata"]["key_id"] == "key_1"
    assert data1["metadata"]["fallback_attempts"] == 0
    assert data1["metadata"]["input_tokens"] == 42
    assert data1["metadata"]["output_tokens"] == 9
    assert mock_completion.call_count == 1

    # 2. Different session asks identical question -> LLM_CACHE
    resp2 = client.post("/chat", json={
        "session_id": "session-france-2",
        "message": "What is the capital of France?"
    })

    assert resp2.status_code == 200
    data2 = resp2.json()
    # Reply text must be identical
    assert data2["reply"] == data1["reply"]
    meta2 = data2["metadata"]
    assert meta2["resolution_source"] == "LLM_CACHE"
    assert meta2["key_id"] is None
    assert meta2["fallback_attempts"] == 0
    # Preserved token usage
    assert meta2["input_tokens"] == 42
    assert meta2["output_tokens"] == 9
    assert isinstance(meta2["latency_ms"], int)

    # litellm.completion must NOT have been called a second time
    assert mock_completion.call_count == 1
