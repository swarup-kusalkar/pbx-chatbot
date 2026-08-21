from sqlalchemy import Column, String, Text, Enum, Integer, ForeignKey, TIMESTAMP, func
from database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum("user", "assistant"), nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(String(100), nullable=False)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    chroma_id = Column(String(36), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )


class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    summary_text = Column(Text, nullable=False)
    up_to_msg_id = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class VoiceSession(Base):
    __tablename__ = "voice_sessions"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    ended_at = Column(TIMESTAMP, nullable=True)


class VoiceTurn(Base):
    __tablename__ = "voice_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum("user", "assistant"), nullable=False)
    transcript = Column(Text, nullable=False)
    audio_duration_ms = Column(Integer, nullable=True)
    was_interrupted = Column(Integer, server_default="0", nullable=False)
    interrupt_at_char = Column(Integer, nullable=True)
    sequence_num = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )