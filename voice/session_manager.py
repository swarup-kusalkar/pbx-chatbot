import asyncio
import logging
from typing import Optional
from sqlalchemy.orm import Session as SQLAlchemySession

from database import SessionLocal
from models import VoiceSession as VoiceSessionModel, VoiceTurn as VoiceTurnModel

log = logging.getLogger(__name__)


class VoiceSession:
    def __init__(self, session_id: str, voice_session_id: str):
        self.session_id = session_id
        self.voice_session_id = voice_session_id
        self.audio_buffer = bytearray()
        self.cancel_event = asyncio.Event()
        self.is_processing = False
        self.sequence_counter = 0
        self.last_user_transcript: str = ""
        self.interrupted_partial: Optional[str] = None

    def buffer_audio(self, data: bytes) -> None:
        self.audio_buffer.extend(data)

    def flush_audio_buffer(self) -> bytes:
        data = bytes(self.audio_buffer)
        self.audio_buffer.clear()
        return data

    def _next_sequence(self) -> int:
        self.sequence_counter += 1
        return self.sequence_counter

    async def save_user_turn(self, transcript: str, audio_duration_ms: int) -> None:
        seq = self._next_sequence()
        db: SQLAlchemySession = SessionLocal()
        try:
            voice_turn = VoiceTurnModel(
                session_id=self.session_id,
                role="user",
                transcript=transcript,
                audio_duration_ms=audio_duration_ms,
                was_interrupted=False,
                interrupt_at_char=None,
                sequence_num=seq,
            )
            db.add(voice_turn)

            from models import Message
            msg = Message(
                session_id=self.session_id,
                role="user",
                content=transcript,
                token_count=len(transcript) // 4,
            )
            db.add(msg)

            db.commit()
            self.last_user_transcript = transcript
            log.info(f"Saved user voice turn seq={seq}: {transcript[:80]}")
        finally:
            db.close()

    async def save_assistant_turn(
        self,
        text: str,
        interrupted: bool = False,
        interrupt_at_char: Optional[int] = None,
    ) -> None:
        seq = self._next_sequence()
        db: SQLAlchemySession = SessionLocal()
        try:
            voice_turn = VoiceTurnModel(
                session_id=self.session_id,
                role="assistant",
                transcript=text,
                audio_duration_ms=None,
                was_interrupted=interrupted,
                interrupt_at_char=interrupt_at_char,
                sequence_num=seq,
            )
            db.add(voice_turn)

            from models import Message
            content = text
            if interrupted:
                content = text[:interrupt_at_char] + " [interrupted]" if interrupt_at_char else text + " [interrupted]"
            msg = Message(
                session_id=self.session_id,
                role="assistant",
                content=content,
                token_count=len(content) // 4,
            )
            db.add(msg)

            db.commit()
            log.info(f"Saved assistant voice turn seq={seq}, interrupted={interrupted}")
        finally:
            db.close()

    def handle_interrupt(self, partial_ai_spoken: str) -> None:
        self.cancel_event.set()
        self.interrupted_partial = partial_ai_spoken
        interrupt_at_char = len(partial_ai_spoken) if partial_ai_spoken else None
        asyncio.create_task(self.save_assistant_turn(partial_ai_spoken, interrupted=True, interrupt_at_char=interrupt_at_char))

    async def cleanup(self) -> None:
        self.cancel_event.set()
        self.is_processing = False
        db: SQLAlchemySession = SessionLocal()
        try:
            vs = db.query(VoiceSessionModel).filter(VoiceSessionModel.id == self.voice_session_id).first()
            if vs:
                from sqlalchemy import func
                vs.ended_at = func.now()
                db.commit()
        finally:
            db.close()
        self.audio_buffer.clear()


async def create_voice_session(session_id: str) -> VoiceSession:
    import uuid
    from models import Session as SessionModel
    voice_session_id = str(uuid.uuid4())
    db: SQLAlchemySession = SessionLocal()
    try:
        existing = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not existing:
            new_session = SessionModel(id=session_id)
            db.add(new_session)
            db.flush()

        vs = VoiceSessionModel(
            id=voice_session_id,
            session_id=session_id,
        )
        db.add(vs)
        db.commit()
        log.info(f"Created voice session {voice_session_id} for session {session_id}")
    finally:
        db.close()
    return VoiceSession(session_id, voice_session_id)