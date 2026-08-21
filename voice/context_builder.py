import logging
from typing import List, Optional
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy import desc

from database import SessionLocal
from models import Message, VoiceTurn

log = logging.getLogger(__name__)


def build_history_messages(session_id: str) -> List[dict]:
    db: SQLAlchemySession = SessionLocal()
    try:
        messages = db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(desc(Message.id)).limit(6).all()

        messages = list(reversed(messages))

        result = []
        for msg in messages:
            content = msg.content
            vt = db.query(VoiceTurn).filter(
                VoiceTurn.session_id == session_id,
                VoiceTurn.transcript == content,
                VoiceTurn.role == msg.role
            ).order_by(desc(VoiceTurn.id)).first()

            if vt and vt.was_interrupted and msg.role == "assistant":
                if vt.interrupt_at_char is not None:
                    content = content[:vt.interrupt_at_char] + " [interrupted mid-response]"
                else:
                    content = content + " [interrupted mid-response]"

            result.append({"role": msg.role, "content": content})

        return result
    finally:
        db.close()


def build_context_text(rag_chunks: List[str], interrupted_partial: Optional[str]) -> str:
    lines = ["KNOWLEDGE BASE CONTEXT:"]
    for chunk in rag_chunks:
        lines.append("---")
        lines.append(chunk.strip())
    lines.append("---")
    lines.append("")

    if interrupted_partial:
        lines.append(
            f"NOTE: In your previous response you said '{interrupted_partial}' before being interrupted. "
            f"The user has now asked a new question. Do not re-answer the previous question unless asked."
        )
        lines.append("")

    lines.append("Answer the user's spoken question using the knowledge base context above.")
    return "\n".join(lines)