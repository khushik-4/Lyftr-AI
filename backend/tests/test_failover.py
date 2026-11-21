from unittest.mock import patch
from litellm.exceptions import RateLimitError, APIError
from tests.conftest import make_mock_response
from app.config import settings


@patch("litellm.completion")
def test_failover_on_429(mock_completion, client):
    # key_1 fails with 429, key_2 succeeds
    mock_completion.side_effect = [
        RateLimitError(
            message="Rate limit exceeded",
            model="gemini/gemini-2.0-flash",
            llm_provider="gemini"
        ),
        make_mock_response("Success on key_2!", prompt_tokens=25, completion_tokens=10)
    ]

    response = client.post("/chat", json={
        "session_id": "sess-failover-1",
        "message": "Testing failover"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "Success on key_2!"
    metadata = data["metadata"]
    assert metadata["key_id"] == "key_2"
    assert metadata["fallback_attempts"] == 1
    assert metadata["resolution_source"] == "LIVE_INFERENCE"


@patch("litellm.completion")
def test_failover_on_500_and_503(mock_completion, client):
    # key_1 fails with 500, key_2 succeeds
    mock_completion.side_effect = [
        APIError(
            status_code=500,
            message="Internal Server Error",
            model="gemini/gemini-2.0-flash",
            llm_provider="gemini"
        ),
        make_mock_response("Success after 500 error")
    ]

    response = client.post("/chat", json={
        "session_id": "sess-failover-500",
        "message": "Testing 500 error failover"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["key_id"] == "key_2"
    assert data["metadata"]["fallback_attempts"] == 1


@patch("litellm.completion")
def test_all_keys_failed_returns_503(mock_completion, client):
    # Both keys fail
    mock_completion.side_effect = [
        RateLimitError(message="Rate limit key 1", model="gemini", llm_provider="gemini"),
        RateLimitError(message="Rate limit key 2", model="gemini", llm_provider="gemini")
    ]

    session_id = "sess-all-fail"
    response = client.post("/chat", json={
        "session_id": session_id,
        "message": "Will fail completely"
    })

    assert response.status_code == 503
    assert response.json() == {"detail": "all providers unavailable"}

    # Verify nothing was added to SQLite for failed request
    hist_resp = client.get(f"/sessions/{session_id}/messages")
    assert hist_resp.status_code == 404


@patch("litellm.completion")
def test_simulate_failure_key_1_429(mock_completion, client):
    mock_completion.return_value = make_mock_response("Answer from key_2")

    response = client.post(
        "/chat",
        headers={"X-Simulate-Failure": "key_1=429"},
        json={
            "session_id": "sess-sim-1",
            "message": "Test simulated failover"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "Answer from key_2"
    assert data["metadata"]["key_id"] == "key_2"
    assert data["metadata"]["fallback_attempts"] == 1


@patch("litellm.completion")
def test_simulate_failure_all_keys_wildcard(mock_completion, client):
    response = client.post(
        "/chat",
        headers={"X-Simulate-Failure": "*=429"},
        json={
            "session_id": "sess-sim-all",
            "message": "Test simulated all fail"
        }
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "all providers unavailable"}

    # litellm should not have even been called for simulated *=429
    assert mock_completion.call_count == 0

    # Ensure nothing saved in database
    hist_resp = client.get("/sessions/sess-sim-all/messages")
    assert hist_resp.status_code == 404


@patch("litellm.completion")
def test_simulate_failure_bypasses_cache(mock_completion, client):
    mock_completion.return_value = make_mock_response("Cached answer")

    # Step 1: Prime cache with a normal call
    r1 = client.post("/chat", json={
        "session_id": "sess-cache-prime",
        "message": "What is 2+2?"
    })
    assert r1.status_code == 200
    assert r1.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"

    # Step 2: Call again with X-Simulate-Failure: key_1=429
    # It must bypass cache and hit key_2!
    r2 = client.post(
        "/chat",
        headers={"X-Simulate-Failure": "key_1=429"},
        json={
            "session_id": "sess-sim-bypass",
            "message": "What is 2+2?"
        }
    )
    assert r2.status_code == 200
    data2 = r2.json()
    # Must be live inference on key_2, not hidden by cache!
    assert data2["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert data2["metadata"]["key_id"] == "key_2"
    assert data2["metadata"]["fallback_attempts"] == 1


@patch("litellm.completion")
def test_simulate_failure_disabled(mock_completion, client):
    mock_completion.return_value = make_mock_response("Normal answer from key_1")

    # Temporarily disable failure simulation
    settings.ENABLE_FAILURE_SIMULATION = False
    try:
        response = client.post(
            "/chat",
            headers={"X-Simulate-Failure": "key_1=429"},
            json={
                "session_id": "sess-sim-disabled",
                "message": "Testing with simulation disabled"
            }
        )
        assert response.status_code == 200
        # Should use key_1 since header is ignored
        assert response.json()["metadata"]["key_id"] == "key_1"
        assert response.json()["metadata"]["fallback_attempts"] == 0
    finally:
        settings.ENABLE_FAILURE_SIMULATION = True
