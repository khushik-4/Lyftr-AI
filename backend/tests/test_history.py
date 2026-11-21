from unittest.mock import patch
from tests.conftest import make_mock_response


@patch("litellm.completion")
def test_multi_turn_context_and_history(mock_completion, client):
    mock_completion.side_effect = [
        make_mock_response("Nice to meet you, Alex!"),
        make_mock_response("Your name is Alex.")
    ]

    session_id = "session_test_memory"

    # Turn 1
    resp1 = client.post("/chat", json={
        "session_id": session_id,
        "message": "My name is Alex."
    })
    assert resp1.status_code == 200

    # Verify first call messages
    first_call_args = mock_completion.call_args_list[0][1]
    messages_turn_1 = first_call_args["messages"]
    assert any(m["role"] == "user" and m["content"] == "My name is Alex." for m in messages_turn_1)

    # Turn 2
    resp2 = client.post("/chat", json={
        "session_id": session_id,
        "message": "What is my name?"
    })
    assert resp2.status_code == 200

    # Verify second call includes history
    second_call_args = mock_completion.call_args_list[1][1]
    messages_turn_2 = second_call_args["messages"]

    # History order: system, user 1, assistant 1, user 2
    contents = [m["content"] for m in messages_turn_2]
    assert "My name is Alex." in contents
    assert "Nice to meet you, Alex!" in contents
    assert "What is my name?" in contents

    # Test GET /sessions/{session_id}/messages
    hist_resp = client.get(f"/sessions/{session_id}/messages")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert hist_data["session_id"] == session_id
    msgs = hist_data["messages"]
    assert len(msgs) == 4  # 2 user msgs + 2 assistant msgs

    # Verify oldest first
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "My name is Alex."
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == "Nice to meet you, Alex!"
    assert msgs[1]["metadata"]["resolution_source"] == "LIVE_INFERENCE"

    assert msgs[2]["role"] == "user"
    assert msgs[2]["content"] == "What is my name?"
    assert msgs[3]["role"] == "assistant"
    assert msgs[3]["content"] == "Your name is Alex."


@patch("litellm.completion")
def test_session_isolation(mock_completion, client):
    mock_completion.return_value = make_mock_response("Response to session")

    # Session A
    client.post("/chat", json={"session_id": "sess_A", "message": "Secret A"})

    # Session B
    client.post("/chat", json={"session_id": "sess_B", "message": "Secret B"})

    # Check Session A history
    hist_A = client.get("/sessions/sess_A/messages").json()
    contents_A = [m["content"] for m in hist_A["messages"]]
    assert "Secret A" in contents_A
    assert "Secret B" not in contents_A

    # Check Session B history
    hist_B = client.get("/sessions/sess_B/messages").json()
    contents_B = [m["content"] for m in hist_B["messages"]]
    assert "Secret B" in contents_B
    assert "Secret A" not in contents_B


def test_unknown_session_returns_404(client):
    response = client.get("/sessions/non_existent_session_999/messages")
    assert response.status_code == 404
    assert response.json()["detail"] == "session not found"
