import os
import json
from typing import Generator, List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
from app.models import Base, Message

# Ensure directory for SQLite database exists if using file path
def _ensure_db_dir(db_url: str):
    if db_url.startswith("sqlite:///"):
        file_path = db_url.replace("sqlite:///", "")
        # Handle 4 slashes like sqlite:////data/app.db
        if file_path.startswith("/"):
            # unix style absolute path
            dir_name = os.path.dirname(file_path)
            if dir_name:
                try:
                    os.makedirs(dir_name, exist_ok=True)
                except Exception:
                    pass
        else:
            dir_name = os.path.dirname(file_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

_ensure_db_dir(settings.DATABASE_URL)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables on application startup."""
    _ensure_db_dir(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)


def check_db_connection() -> bool:
    """Verify database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_messages(db: Session, session_id: str) -> List[Message]:
    """Retrieve messages for a session ordered oldest first."""
    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.id.asc())
        .all()
    )


def session_exists(db: Session, session_id: str) -> bool:
    """Check if any message exists for a session."""
    return db.query(Message).filter(Message.session_id == session_id).first() is not None


def save_chat_turn(
    db: Session,
    session_id: str,
    user_content: str,
    assistant_content: str,
    assistant_metadata: Dict[str, Any]
) -> None:
    """Persist a user message and assistant message atomically."""
    now_iso = datetime.now(timezone.utc).isoformat()
    user_msg = Message(
        session_id=session_id,
        role="user",
        content=user_content,
        metadata_json=None,
        created_at=now_iso
    )
    assistant_msg = Message(
        session_id=session_id,
        role="assistant",
        content=assistant_content,
        metadata_json=json.dumps(assistant_metadata),
        created_at=now_iso
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()

