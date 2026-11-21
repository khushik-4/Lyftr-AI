const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Check backend health status
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) {
      throw new Error(`Health check failed with status ${response.status}`);
    }
    return await response.json();
  } catch (err) {
    throw err;
  }
}

/**
 * Send a chat message to POST /chat
 */
export async function sendChatMessage({
  sessionId,
  message,
  systemPrompt,
  simulateFailureHeader
}) {
  const headers = {
    'Content-Type': 'application/json'
  };

  // Only include header when active
  if (simulateFailureHeader && simulateFailureHeader.trim() !== '') {
    headers['X-Simulate-Failure'] = simulateFailureHeader.trim();
  }

  const payload = {
    session_id: sessionId,
    message: message
  };

  if (systemPrompt && systemPrompt.trim() !== '') {
    payload.system_prompt = systemPrompt.trim();
  }

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload)
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    if (response.status === 422) {
      const detailMsg = Array.isArray(data.detail)
        ? data.detail.map(d => d.msg || JSON.stringify(d)).join(', ')
        : data.detail || 'Validation error: message must be between 1 and 4000 characters.';
      const err = new Error(detailMsg);
      err.status = 422;
      throw err;
    }

    if (response.status === 503) {
      const err = new Error(
        data.detail === 'all providers unavailable'
          ? 'All AI providers are currently unavailable. Please try again in a moment.'
          : data.detail || 'All AI providers are currently unavailable.'
      );
      err.status = 503;
      throw err;
    }

    const err = new Error(data.detail || `Server error (${response.status})`);
    err.status = response.status;
    throw err;
  }

  return data;
}

/**
 * Fetch stored message history for a session
 */
export async function getSessionMessages(sessionId) {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const err = new Error(data.detail || `Failed to fetch session messages (${response.status})`);
    err.status = response.status;
    throw err;
  }

  return data;
}

