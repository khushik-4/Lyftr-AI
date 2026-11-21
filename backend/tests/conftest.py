import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Disable remote cost map fetch and telemetry for speed and offline stability
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "true"
os.environ["LLM_API_KEYS"] = "test_key_1,test_key_2"
os.environ["LLM_MODEL"] = "gemini/gemini-2.0-flash"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENABLE_FAILURE_SIMULATION"] = "true"

from litellm import ModelResponse, Choices, Message, Usage
from app.main import app
from app.models import Base
from app.database import get_db
from app.cache_service import cache_service

# Create an in-memory test database engine with StaticPool so all connections share the same memory DB
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    # Clear in-memory cache before each test
    try:
        if hasattr(cache_service.cache.cache, "cache_dict"):
            cache_service.cache.cache.cache_dict.clear()
    except Exception:
        pass
    yield
    Base.metadata.drop_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def make_mock_response(content: str, prompt_tokens: int = 15, completion_tokens: int = 8) -> ModelResponse:
    return ModelResponse(
        id="mock-resp-id",
        choices=[Choices(message=Message(content=content, role="assistant"))],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
    )
