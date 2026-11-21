import json
from contextlib import asynccontextmanager
from typing import Optional, List, Dict
from fastapi import FastAPI, Depends, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.config import settings
from app.database import init_db, check_db_connection, get_db, get_session_messages, session_exists, save_chat_turn
from app.exceptions import AllProvidersUnavailableException, SessionNotFoundException
from app.schemas import (
    HealthResponse,
    ChatRequest,
    ChatResponse,
    SessionMessagesResponse,
    StoredMessage
)
from app.llm_service import llm_service
from app.cache_service import cache_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables are created
    init_db()
    yield


app = FastAPI(
    title="Lyftr AI API",
    description="Resilient LLM Chatbot API with Key Failover and Response Caching",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
origins = settings.get_allowed_origins_list()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True if "*" not in origins else False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Exception Handlers ensuring consistent JSON responses with "detail"
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": jsonable_encoder(exc.errors())}
    )


@app.exception_handler(AllProvidersUnavailableException)
async def all_providers_exception_handler(request: Request, exc: AllProvidersUnavailableException):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": exc.detail}
    )


@app.exception_handler(SessionNotFoundException)
async def session_not_found_handler(request: Request, exc: SessionNotFoundException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.detail}
    )


@app.exception_handler(HTTPException)
async def generic_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never expose unhandled tracebacks or HTML errors
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred."}
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint"
)
def get_health():
    """Returns 200 once app is running, DB is reachable, and key pool is loaded."""
    db_ok = check_db_connection()
    if not db_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )

    keys = settings.get_parsed_keys()
    return HealthResponse(
        status="ok",
        keys_configured=len(keys),
        cache_enabled=cache_service.is_enabled()
    )


@app.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send chat message"
)
async def post_chat(
    payload: ChatRequest,
    x_simulate_failure: Optional[str] = Header(None, alias="X-Simulate-Failure"),
    db: Session = Depends(get_db)
):
    """
    Process a chat message with multi-turn memory, caching, and failover.
    Failed requests are never saved to SQLite.
    """
    session_id = payload.session_id
    user_message = payload.message
    custom_system_prompt = payload.system_prompt or settings.DEFAULT_SYSTEM_PROMPT

    # 1. Fetch previous session history from SQLite (oldest first)
    previous_messages = get_session_messages(db, session_id)

    # 2. Build complete LLM message list:
    #    [System prompt, ...Previous messages, Current user message]
    llm_messages: List[Dict[str, str]] = [
        {"role": "system", "content": custom_system_prompt}
    ]

    for msg in previous_messages:
        llm_messages.append({"role": msg.role, "content": msg.content})

    llm_messages.append({"role": "user", "content": user_message})

    # 3. Execute chat via LLM Service (handles cache check, failure simulation, failover)
    reply_text, metadata = await llm_service.execute_chat(
        messages=llm_messages,
        simulate_failure_header=x_simulate_failure
    )

    # 4. On success only, atomically persist turn into SQLite
    save_chat_turn(
        db=db,
        session_id=session_id,
        user_content=user_message,
        assistant_content=reply_text,
        assistant_metadata=metadata.model_dump()
    )

    return ChatResponse(
        session_id=session_id,
        reply=reply_text,
        metadata=metadata
    )


@app.get(
    "/sessions/{session_id}/messages",
    response_model=SessionMessagesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get session message history"
)
def get_session_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns stored history of one session from SQLite, oldest first, without system prompt.
    Returns 404 if session is unknown.
    """
    if not session_exists(db, session_id):
        raise SessionNotFoundException("session not found")

    messages = get_session_messages(db, session_id)
    stored_msgs: List[StoredMessage] = []

    for msg in messages:
        meta_dict = None
        if msg.role == "assistant" and msg.metadata_json:
            try:
                meta_dict = json.loads(msg.metadata_json)
            except Exception:
                meta_dict = None

        stored_msgs.append(
            StoredMessage(
                role=msg.role,
                content=msg.content,
                metadata=meta_dict
            )
        )

    return SessionMessagesResponse(
        session_id=session_id,
        messages=stored_msgs
    )
