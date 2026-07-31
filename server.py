import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

from database import engine, Base, SessionLocal
from models import Session as SessionModel, Message, KnowledgeBase, ConversationSummary
from schemas import (
    ChatRequest, ChatResponse, ChatResponseData,
    SessionsListResponse, SessionInfo,
    CreateSessionRequest, CreateSessionResponse,
    HistoryResponse, HistoryResponseData, MessageInfo,
    DeleteSessionResponse, KnowledgeResponse, ArticleInfo,
)
from rag.retriever import retrieve_kb_chunks
from rag.vector_store import get_collection_count
from llm.llm_client import call_llm, LLMUnavailableError
from llm.prompt_builder import build_prompt
from config import config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def _run_summary_update(session_id: str):
    from context.compressor import update_summary_if_needed
    try:
        update_summary_if_needed(session_id)
    except Exception as e:
        log.error(f"Summary update failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting PBX Chatbot server...")
    Base.metadata.create_all(bind=engine)
    log.info("Database tables verified.")

    try:
        count = get_collection_count()
        log.info(f"ChromaDB collection has {count} chunks.")
        if count == 0:
            log.warning("ChromaDB is empty. Running auto-seed...")
            from scripts.seed_kb import create_tables, seed_articles, verify
            create_tables()
            seed_articles()
            verify()
            log.info("Auto-seed complete.")
    except Exception as e:
        log.warning(f"ChromaDB check failed: {e}. Will retry on first request.")

    yield
    log.info("Shutting down...")


app = FastAPI(title="PBX Support Chatbot", version="1.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="public"), name="static")


@app.get("/")
async def root():
    from fastapi.responses import FileResponse
    return FileResponse("public/index.html")


@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import Response
    return Response(content="", status_code=204)


# ─── Chat Route ───────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    db = SessionLocal()
    try:
        existing = db.query(SessionModel).filter(SessionModel.id == req.session_id).first()
        if not existing:
            new_session = SessionModel(id=req.session_id)
            db.add(new_session)
            db.commit()

        user_msg = Message(
            session_id=req.session_id,
            role="user",
            content=req.message,
            token_count=len(req.message) // 4
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        if not existing:
            existing = new_session
            existing.title = req.message[:80]
            db.commit()

        chunks = retrieve_kb_chunks(req.message, n_results=3)
        retrieved_topics = list(dict.fromkeys(c["topic"] for c in chunks))

        from context.compressor import build_conversation_context
        history = build_conversation_context(req.session_id)

        prompt = build_prompt(kb_chunks=chunks, history=history, current_message=req.message)

        try:
            reply_text, llm_used = await call_llm(prompt)
        except LLMUnavailableError as e:
            return ChatResponse(
                success=False,
                data=None,
                error={"code": "LLM_UNAVAILABLE", "message": str(e)}
            )
        except Exception as e:
            log.error(f"Chat error: {e}")
            if "Can't connect" in str(e) or "Lost connection" in str(e) or "Connection refused" in str(e):
                return ChatResponse(success=False, data=None, error={"code": "DB_UNAVAILABLE", "message": "Database unavailable. Please try again."})
            return ChatResponse(success=False, data=None, error={"code": "INTERNAL_ERROR", "message": str(e)})

        assistant_msg = Message(
            session_id=req.session_id,
            role="assistant",
            content=reply_text,
            token_count=len(reply_text) // 4
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        existing.title = user_msg.content[:80] if not existing.title else existing.title
        db.commit()

        from context.compressor import update_summary_if_needed
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_run_summary_update(req.session_id))
            else:
                update_summary_if_needed(req.session_id)
        except Exception:
            update_summary_if_needed(req.session_id)

        return ChatResponse(
            success=True,
            data=ChatResponseData(
                reply=reply_text,
                session_id=req.session_id,
                retrieved_topics=retrieved_topics,
                llm_used=llm_used,
                message_id=assistant_msg.id
            )
        )

    except Exception as e:
        log.error(f"Chat error: {e}")
        return ChatResponse(success=False, data=None, error={"code": "INTERNAL_ERROR", "message": str(e)})
    finally:
        db.close()


# ─── Sessions Routes ────────────────────────────────────────────

@app.get("/api/sessions", response_model=SessionsListResponse)
async def list_sessions():
    db = SessionLocal()
    try:
        sessions = db.query(SessionModel).order_by(SessionModel.updated_at.desc()).all()
        result = []
        for s in sessions:
            msg_count = db.query(Message).filter(Message.session_id == s.id).count()
            result.append(SessionInfo(
                id=s.id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=msg_count
            ))
        return SessionsListResponse(success=True, data=result)
    finally:
        db.close()


@app.post("/api/sessions", response_model=CreateSessionResponse)
async def create_session(req: CreateSessionRequest):
    db = SessionLocal()
    try:
        existing = db.query(SessionModel).filter(SessionModel.id == req.session_id).first()
        if not existing:
            new_session = SessionModel(id=req.session_id)
            db.add(new_session)
            db.commit()
        return CreateSessionResponse(success=True, data={"session_id": req.session_id, "title": None})
    finally:
        db.close()


@app.get("/api/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str):
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        messages = db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.created_at).all()

        msg_list = [
            MessageInfo(id=m.id, role=m.role, content=m.content, created_at=m.created_at)
            for m in messages
        ]

        return HistoryResponse(
            success=True,
            data=HistoryResponseData(
                session_id=session_id,
                title=session.title,
                messages=msg_list
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"History error: {e}")
        return HistoryResponse(success=False, data=None, error={"code": "INTERNAL_ERROR", "message": str(e)})
    finally:
        db.close()


@app.delete("/api/sessions/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(session_id: str):
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        db.query(ConversationSummary).filter(ConversationSummary.session_id == session_id).delete()
        db.query(Message).filter(Message.session_id == session_id).delete()
        db.delete(session)
        db.commit()

        return DeleteSessionResponse(success=True, data={"deleted_session_id": session_id})
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Delete session error: {e}")
        return DeleteSessionResponse(success=False, data=None, error={"code": "INTERNAL_ERROR", "message": str(e)})
    finally:
        db.close()


# ─── Knowledge Base Route ────────────────────────────────────────

@app.get("/api/knowledge", response_model=KnowledgeResponse)
async def get_knowledge():
    db = SessionLocal()
    try:
        articles = db.query(KnowledgeBase).all()
        result = [
            ArticleInfo(id=a.id, topic=a.topic, question=a.question, answer=a.answer)
            for a in articles
        ]
        return KnowledgeResponse(success=True, data=result)
    finally:
        db.close()


# ─── Export Route ────────────────────────────────────────────────

@app.get("/api/export/{session_id}")
async def export_chat(session_id: str):
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        messages = db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.created_at).all()

        lines = [
            "PBX Support Chatbot — Conversation Export",
            f"Session: {session_id}",
            f"Exported: {messages[0].created_at if messages else 'N/A'}",
            "=" * 50,
            ""
        ]

        for msg in messages:
            role = "You" if msg.role == "user" else "Assistant"
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S") if msg.created_at else ""
            lines.append(f"[{timestamp}] {role}: {msg.content}")
            lines.append("")

        lines.append("=" * 50)
        lines.append("End of conversation")

        content = "\n".join(lines)
        return Response(content=content, media_type="text/plain")
    finally:
        db.close()


# ─── Startup check ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=config.APP_PORT, reload=True)