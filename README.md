# Lyftr AI — Full-Stack LLM Chatbot with Key Failover & Response Caching

Lyftr AI is a lightweight, resilient full-stack AI chatbot engineered with **FastAPI**, **LiteLLM**, **SQLite**, **React**, and **Vite**. It delivers multi-turn conversational context, automatic sequential API key failover, built-in response caching, per-request token tracking, and latency profiling wrapped in a minimal, warm editorial SaaS interface.

---

## 1. Live URLs

| Service | Target URL | Notes |
|---|---|---|
| **Frontend Application** | `https://lyftr-ai.vercel.app` *(Placeholder pending deployment credentials)* | React SPA hosted on Vercel |
| **Backend API** | `https://lyftr-ai.onrender.com` *(Placeholder pending deployment credentials)* | FastAPI backend hosted on Render |
| **Health Check Endpoint** | `https://lyftr-ai.onrender.com/health` | Live system & key pool status |
| **GitHub Repository** | `https://github.com/your-username/lyftr-ai` | Full source code with tests |

---

## 2. Run locally: with Docker and without

### Prerequisites
- **Git**
- **Docker & Docker Compose** (for containerized mode)
- **Node.js (v18+) & npm** (for local frontend execution)
- **Python (3.11+)** (for local backend execution)
- At least two Gemini API keys (or compatible LiteLLM provider keys)

---

### Method A: Running with Docker (Recommended)

1. **Clone the repository and enter the directory**:
   ```powershell
   git clone https://github.com/your-username/lyftr-ai.git
   cd lyftr-ai
   ```

2. **Configure your environment**:
   Copy `.env.example` to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
   Edit `.env` and set your actual API keys:
   ```env
   LLM_API_KEYS=your_first_gemini_key,your_second_gemini_key
   LLM_MODEL=gemini/gemini-2.0-flash
   DATABASE_URL=sqlite:////data/app.db
   ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
   ENABLE_FAILURE_SIMULATION=true
   ```

3. **Start the stack using Make or Docker Compose**:
   ```powershell
   # If Make is available:
   make up

   # Or using Docker Compose directly:
   docker compose up --build -d
   ```

4. **Access the applications**:
   - **Frontend UI**: [http://localhost:3000](http://localhost:3000)
   - **Backend API**: [http://localhost:8000](http://localhost:8000)
   - **Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

5. **Stop the stack**:
   ```powershell
   make down
   # or: docker compose down
   ```

*Note: Database history persists across container stops and rebuilds inside the named volume `lyftr_sqlite_data` mounted at `/data`.*

---

### Method B: Running locally without Docker

#### 1. Backend Setup (FastAPI)
Open a PowerShell terminal:
```powershell
# Navigate to backend directory
cd backend

# Create a virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create .env file with your credentials
Set-Content -Path .env -Value @"
LLM_API_KEYS=your_first_gemini_key,your_second_gemini_key
LLM_MODEL=gemini/gemini-2.0-flash
DATABASE_URL=sqlite:///./data/app.db
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
ENABLE_FAILURE_SIMULATION=true
"@

# Start FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup (React + Vite)
Open a second PowerShell terminal:
```powershell
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 3. Design decisions: key fallback, caching, SQLite session storage

### Key Fallback Mechanism
- **Why multiple keys?** Free-tier and production LLM APIs enforce strict rate limits (HTTP 429) and can suffer transient infrastructure blips (HTTP 500, 502, 503). A multi-key pool ensures continuous uptime without user disruptions.
- **Key selection & ordering:** Keys are parsed from `LLM_API_KEYS` into indexed identifiers (`key_1`, `key_2`, ...). LiteLLM always starts with `key_1`.
- **Transient error detection:** If `key_1` throws a `RateLimitError`, `BudgetExceededError`, `APIConnectionError`, or returns HTTP 429/5xx, the service logs the attempt, increments `fallback_attempts`, and automatically transfers the request to `key_2`.
- **Clean 503 termination:** If all configured keys fail, the service returns HTTP 503 with `{"detail": "all providers unavailable"}` and never inserts a broken record into history.
- **Failover simulation:** When `ENABLE_FAILURE_SIMULATION=true`, the `X-Simulate-Failure` header (e.g. `key_1=429` or `*=429`) mocks provider failure for that specific request only, bypassing response-cache lookup so failovers can be verified on demand without burning real provider quota.

### Response Caching
- **LiteLLM built-in caching:** We utilize LiteLLM's internal caching architecture (`Cache(type="local", max_messages=None)`), guaranteeing compatibility with native LiteLLM response schemas.
- **Cache key structure:** The cache key is computed from `model + complete message list` (system prompt + historical messages + new message). 
- **Session isolation vs cache sharing:** The `session_id` is purposely excluded from the cache key. Therefore, if two different sessions ask the exact same initial question, Session 2 immediately receives a cache hit (`LLM_CACHE`) in <5ms. However, once conversation histories diverge, the message list diverges, ensuring context isolation.
- **Preserved metrics on cache hit:** Cache hits return the exact original text, identical stored `input_tokens` and `output_tokens`, `key_id = null`, `fallback_attempts = 0`, and the fast cache lookup latency.

### SQLite Session Storage
- **Schema:**
  ```sql
  CREATE TABLE messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id TEXT NOT NULL,
      role TEXT NOT NULL,
      content TEXT NOT NULL,
      metadata TEXT,
      created_at TEXT NOT NULL
  );
  ```
- **Session isolation:** Every session ID partitions conversation history. On each turn, the backend retrieves prior messages for that `session_id` ordered chronologically, constructs the context array `[system_prompt, ...history, current_user_message]`, and queries the LLM.
- **Atomic persistence:** Only completed, successful responses are stored into SQLite. Failed requests (422, 503) are never recorded.
- **Why SQLite over PostgreSQL or Redis?**
  1. *Zero external runtime dependencies:* SQLite is embedded in Python's standard library, completely eliminating database connection crashes and infrastructure overhead.
  2. *Docker volume persistence:* A single persistent volume mounted at `/data/app.db` survives container teardowns and restarts.
  3. *Ideal for session-based workloads:* SQLite easily supports hundreds of concurrent reads with WAL mode and transaction atomicity.

---

## 4. Verification: how to see failover, cache hits and per-message token usage

Run these verification tests from PowerShell using `Invoke-RestMethod`:

### 1. Health Check
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET
```
**Expected Response (200 OK):**
```json
{
  "status": "ok",
  "keys_configured": 2,
  "cache_enabled": true
}
```

---

### 2. Normal Chat (Live Inference)
```powershell
$body = @{
    session_id = "test-session-alpha"
    message = "What is the capital of France?"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://localhost:8000/chat" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```
**Expected Response:**
```json
{
  "session_id": "test-session-alpha",
  "reply": "The capital of France is Paris.",
  "metadata": {
    "resolution_source": "LIVE_INFERENCE",
    "model": "gemini/gemini-2.0-flash",
    "latency_ms": 780,
    "input_tokens": 28,
    "output_tokens": 8,
    "key_id": "key_1",
    "fallback_attempts": 0
  }
}
```

---

### 3. Response Cache Hit
Send the exact same message using a **different session ID**:
```powershell
$body = @{
    session_id = "test-session-beta"
    message = "What is the capital of France?"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://localhost:8000/chat" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```
**Expected Response:**
```json
{
  "session_id": "test-session-beta",
  "reply": "The capital of France is Paris.",
  "metadata": {
    "resolution_source": "LLM_CACHE",
    "model": "gemini/gemini-2.0-flash",
    "latency_ms": 2,
    "input_tokens": 28,
    "output_tokens": 8,
    "key_id": null,
    "fallback_attempts": 0
  }
}
```
*Notice: `resolution_source` is `LLM_CACHE`, `key_id` is `null`, tokens are identical to the live request, and `latency_ms` drops from hundreds of milliseconds to under 5ms.*

---

### 4. Automatic Key Failover (Simulated 429 on key_1)
```powershell
$body = @{
    session_id = "test-session-failover"
    message = "Explain photosynthesis in one sentence."
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://localhost:8000/chat" `
    -Method POST `
    -ContentType "application/json" `
    -Headers @{"X-Simulate-Failure"="key_1=429"} `
    -Body $body
```
**Expected Response:**
```json
{
  "session_id": "test-session-failover",
  "reply": "Photosynthesis is the biological process by which green plants convert sunlight and carbon dioxide into oxygen and glucose.",
  "metadata": {
    "resolution_source": "LIVE_INFERENCE",
    "model": "gemini/gemini-2.0-flash",
    "latency_ms": 840,
    "input_tokens": 30,
    "output_tokens": 22,
    "key_id": "key_2",
    "fallback_attempts": 1
  }
}
```
*Notice: `key_id` switched to `key_2`, and `fallback_attempts` is `1`.*

---

### 5. All Keys Fail (Simulated Wildcard 429)
```powershell
$body = @{
    session_id = "test-session-exhausted"
    message = "This message will encounter 503."
} | ConvertTo-Json

try {
    Invoke-RestMethod `
        -Uri "http://localhost:8000/chat" `
        -Method POST `
        -ContentType "application/json" `
        -Headers @{"X-Simulate-Failure"="*=429"} `
        -Body $body
} catch {
    $streamReader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
    $streamReader.ReadToEnd()
}
```
**Expected Response (503 Service Unavailable):**
```json
{
  "detail": "all providers unavailable"
}
```

---

### 6. Session Message History
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/sessions/test-session-alpha/messages" -Method GET
```
**Expected Response:**
```json
{
  "session_id": "test-session-alpha",
  "messages": [
    {
      "role": "user",
      "content": "What is the capital of France?"
    },
    {
      "role": "assistant",
      "content": "The capital of France is Paris.",
      "metadata": {
        "resolution_source": "LIVE_INFERENCE",
        "input_tokens": 28,
        "output_tokens": 8
      }
    }
  ]
}
```

---

## 5. Setup Used

- **Editor:** Antigravity (Google DeepMind)
- **AI Coding Assistance:** Antigravity AI
- **Technologies:**
  - Frontend: React 18, Vite 5, Vanilla CSS3 (Custom warm minimal design system)
  - Backend: Python 3.12/3.14, FastAPI 0.165, LiteLLM 1.110, SQLAlchemy 2.1
  - Persistence: SQLite with WAL & StaticPool
  - Orchestration & Containerization: Docker (Multi-stage), Docker Compose
  - Automated Testing: Pytest 9.2, HTTPX, unittest.mock
- **Development Environment:** Windows 11 / PowerShell 7

---

## 6. Bonus features

1. **Custom Session Persona (System Prompt Editor):** A collapsible panel allowing users to set custom system prompts for their active conversation without polluting persistent user message history.
2. **Reliability Test Panel:** An integrated UI dropdown to trigger `key_1=429`, `key_1=500`, and `*=429` failure simulations on the next message with automatic single-turn reset.
3. **Real-time Backend Connectivity Polling:** A live heartbeat indicator in the header that monitors server health every 15 seconds.
4. **Documented Fallback Token Estimation:** Graceful fallback token estimation using LiteLLM token counters if a provider omits usage metadata.
5. **Full Test Suite with Zero Network Dependency:** 17 unit and integration tests verifying all failure cases, cache hit properties, session isolation, and validation rules in <0.3 seconds.

---

## Automated Backend Test Suite

To run all automated tests:
```powershell
cd backend
$env:PYTHONPATH="backend"
pytest -v
```
**Test Results:**
```text
backend/tests/test_caching.py::test_caching_behavior PASSED              [  5%]
backend/tests/test_chat.py::test_validation_missing_session_id PASSED    [ 11%]
backend/tests/test_chat.py::test_validation_empty_message PASSED         [ 17%]
backend/tests/test_chat.py::test_validation_whitespace_only_message PASSED [ 23%]
backend/tests/test_chat.py::test_validation_message_too_long PASSED      [ 29%]
backend/tests/test_chat.py::test_valid_chat_success PASSED               [ 35%]
backend/tests/test_failover.py::test_failover_on_429 PASSED              [ 41%]
backend/tests/test_failover.py::test_failover_on_500_and_503 PASSED      [ 47%]
backend/tests/test_failover.py::test_all_keys_failed_returns_503 PASSED  [ 52%]
backend/tests/test_failover.py::test_simulate_failure_key_1_429 PASSED   [ 58%]
backend/tests/test_failover.py::test_simulate_failure_all_keys_wildcard PASSED [ 64%]
backend/tests/test_failover.py::test_simulate_failure_bypasses_cache PASSED [ 70%]
backend/tests/test_failover.py::test_simulate_failure_disabled PASSED    [ 76%]
backend/tests/test_health.py::test_health_check PASSED                   [ 82%]
backend/tests/test_history.py::test_multi_turn_context_and_history PASSED [ 88%]
backend/tests/test_history.py::test_session_isolation PASSED             [ 94%]
backend/tests/test_history.py::test_unknown_session_returns_404 PASSED   [100%]

======================= 17 passed in 0.23s =======================
```

