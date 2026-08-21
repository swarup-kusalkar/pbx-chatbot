import asyncio
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from rag.retriever import retrieve_kb_chunks

from voice.session_manager import VoiceSession, create_voice_session
from voice.nemotron_client import call_nemotron, NIMParseError, pcm_int16_to_wav, peak_normalize_wav
from voice.tts_client import synthesize, extract_sentence, build_audio_frame
from voice.context_builder import build_history_messages

log = logging.getLogger(__name__)

router = APIRouter()

active_sessions: dict[str, VoiceSession] = {}

VOICE_MIN_UTTERANCE_SAMPLES = int(os.getenv("VOICE_MIN_UTTERANCE_SAMPLES", "8000"))
VOICE_MAX_SENTENCE_BUFFER_WORDS = 4


@router.websocket("/ws/voice/{session_id}")
async def voice_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    log.info(f"Voice WS connected: {session_id}")

    if session_id in active_sessions:
        log.warning(f"Session {session_id} already exists, cleaning up old")
        await active_sessions[session_id].cleanup()

    session = await create_voice_session(session_id)
    active_sessions[session_id] = session

    try:
        while True:
            data = await websocket.receive()
            if "bytes" in data:
                session.buffer_audio(data["bytes"])
            elif "text" in data:
                msg = json.loads(data["text"])
                msg_type = msg.get("type")

                if msg_type == "utterance_end":
                    if session.is_processing:
                        log.warning(f"Session {session_id}: utterance_end received while processing, dropping")
                        continue
                    session.is_processing = True
                    asyncio.create_task(handle_utterance(websocket, session))

                elif msg_type == "interrupt":
                    partial = msg.get("partial_ai_spoken", "")
                    session.handle_interrupt(partial)
                    await websocket.send_text(json.dumps({"type": "interrupt_ack"}))

                elif msg_type == "end_session":
                    break

    except WebSocketDisconnect:
        log.info(f"Voice WS disconnected: {session_id}")
    except Exception as e:
        log.error(f"Voice WS error for {session_id}: {e}")
    finally:
        await session.cleanup()
        active_sessions.pop(session_id, None)


async def handle_utterance(websocket: WebSocket, session: VoiceSession):
    try:
        pcm_bytes = session.flush_audio_buffer()

        if len(pcm_bytes) < VOICE_MIN_UTTERANCE_SAMPLES * 2:
            log.info(f"Utterance too short ({len(pcm_bytes)} bytes), ignoring")
            session.is_processing = False
            return

        if session.cancel_event.is_set():
            session.is_processing = False
            return

        wav_bytes = pcm_int16_to_wav(pcm_bytes)
        wav_bytes = peak_normalize_wav(wav_bytes)

        audio_duration_ms = len(pcm_bytes) // 2 // 16 * 1000

        rag_chunks = []
        try:
            query = session.last_user_transcript if session.last_user_transcript else "PBX technical support"
            chunks = retrieve_kb_chunks(query, n_results=3)
            rag_chunks = [c["text"] for c in chunks]
        except Exception as e:
            log.warning(f"RAG fetch failed: {e}")

        history = build_history_messages(session.session_id)

        await websocket.send_text(json.dumps({"type": "thinking"}))

        sentence_buffer = ""
        full_response_text = ""
        heard_emitted = False

        try:
            async for token_type, token_text in call_nemotron(
                wav_bytes,
                rag_chunks,
                history,
                session.interrupted_partial,
                session.cancel_event,
            ):
                if session.cancel_event.is_set():
                    break

                if token_type == "heard":
                    heard_emitted = True
                    await session.save_user_turn(token_text, audio_duration_ms)
                    await websocket.send_text(json.dumps({
                        "type": "transcript",
                        "text": token_text,
                        "final": True
                    }))
                    session.last_user_transcript = token_text
                    session.interrupted_partial = None

                elif token_type == "token":
                    sentence_buffer += token_text
                    full_response_text += token_text

                    if session.cancel_event.is_set():
                        break

                    sentence = extract_sentence(sentence_buffer)
                    if sentence:
                        sentence_buffer = sentence_buffer[len(sentence):].lstrip()
                        if session.cancel_event.is_set():
                            break

                        wav = await synthesize(sentence)
                        if session.cancel_event.is_set():
                            break

                        frame = build_audio_frame(wav, sentence)
                        await websocket.send_bytes(frame)

        except NIMParseError as e:
            log.warning(f"Nemotron parse error: {e}, using fallback transcript")
            if not heard_emitted:
                fallback_transcript = "[transcript unavailable]"
                await session.save_user_turn(fallback_transcript, audio_duration_ms)
                await websocket.send_text(json.dumps({
                    "type": "transcript",
                    "text": fallback_transcript,
                    "final": True
                }))
                session.last_user_transcript = fallback_transcript
        except Exception as e:
            log.error(f"Nemotron call failed: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e),
                "code": "PIPELINE_ERROR"
            }))

        if not session.cancel_event.is_set():
            if sentence_buffer.strip():
                wav = await synthesize(sentence_buffer.strip())
                frame = build_audio_frame(wav, sentence_buffer.strip())
                await websocket.send_bytes(frame)
                full_response_text += sentence_buffer.strip()

            await session.save_assistant_turn(full_response_text, interrupted=False)
            await websocket.send_text(json.dumps({
                "type": "response_complete",
                "full_text": full_response_text
            }))

    except Exception as e:
        log.error(f"handle_utterance error: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e),
            "code": "PIPELINE_ERROR"
        }))
    finally:
        session.is_processing = False
        session.cancel_event.clear()