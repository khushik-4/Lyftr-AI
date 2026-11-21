# Lyftr AI — Project Plan & System Architecture

## Overview
Lyftr AI is a production-grade, lightweight AI chatbot application built with FastAPI, LiteLLM, SQLite, React, and Vite. It provides multi-turn conversational memory, sequential API key failover across configured keys, LiteLLM-powered response caching, per-request token usage tracking, and latency tracking.

---

## 1. System Architecture

```text
+-----------------------------------------------------------+
|                   Client (React / Vite)                   |
|  - Minimal Warm SaaS Theme (#F7F5E9, #858B59, #303329)    |
|  - Multi-turn Chat Window & Message Metadata              |
|  - Reliability Test Panel (X-Simulate-Failure header)     |
|  - Optional System Prompt Customizer                      |
+-----------------------------+-----------------------------+
                              | HTTP / JSON (CORS enabled)
                              v
+-----------------------------------------------------------+
|                   FastAPI Backend API                     |
|  GET  /health                                             |
|  POST /chat                                               |
|  GET  /sessions/{session_id}/messages                     |
+--------------+-----------------------------+--------------+
               |                             |
               v                             v
+------------------------------+  +-------------------------+
|   SQLite Persistent Store    |  |    LiteLLM Gateway      |
|  - messages table            |  |  - Key pool (key_1...)  |
|  - server ISO-8601 timestamps|  |  - Sequential Failover  |
|  - metadata JSON             |  |  - LiteLLM Cache        |
|  - volume mounted at /data   |  |  - Simulated Failures   |
+------------------------------+  +-------------------------+
```

---

## 2. API Contract & Data Flow

### Endpoints
1. `GET /health`
   - Returns `{ "status": "ok", "keys_configured": N, "cache_enabled": true }`
2. `POST /chat`
   - Accepts `{ "session_id": "...", "message": "...", "system_prompt": "..." }`
   - Validates session_id (1-128 chars), message (1-4000 chars non-empty)
   - Checks LiteLLM cache with key `model + full_messages` (bypassed if `X-Simulate-Failure` is present)
   - If cache hit: returns `LLM_CACHE`, `key_id: null`, `fallback_attempts: 0`, cached token counts, lookup latency.
   - If cache miss: iterates through key pool (`key_1`, `key_2`, ...). On retryable errors (429, 500, 502, 503, quota), attempts fallback.
   - Stores user message & assistant message with metadata into SQLite upon success.
   - On total failure: returns 503 `{"detail": "all providers unavailable"}` and writes nothing to SQLite.
3. `GET /sessions/{session_id}/messages`
   - Retrieves stored history for the session ordered oldest first.
   - Returns 404 if session not found.

---

## 3. Directory Layout
- `backend/app`: FastAPI application, configuration, models, database, LiteLLM service, cache service.
- `backend/tests`: Pytest suite testing health, validation, multi-turn, caching, failover, and history.
- `frontend/src`: React application components, hooks, API services, and styles conforming to data-testid requirements.
- `docker-compose.yml`, `Makefile`, `.env.example`, `README.md`.
