from sqlalchemy import Column, Integer, String, Text, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(128), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    metadata_json = Column("metadata", Text, nullable=True)  # JSON string for assistant messages
    created_at = Column(String(64), nullable=False)  # ISO-8601 format

    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
    )
