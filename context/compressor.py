from database import SessionLocal
from models import Message, ConversationSummary
from config import config
from llm.llm_client import call_llm


MAX_HISTORY = config.MAX_HISTORY_MESSAGES
SUMMARY_TRIGGER = config.SUMMARY_TRIGGER_COUNT
RECENT_AFTER_SUMMARY = config.RECENT_MESSAGES_AFTER_SUMMARY


def count_messages(session_id: str) -> int:
    db = SessionLocal()
    try:
        return db.query(Message).filter(Message.session_id == session_id).count()
    finally:
        db.close()


def fetch_all_messages(session_id: str) -> list:
    db = SessionLocal()
    try:
        messages = db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.created_at).all()
        return [{"id": m.id, "role": m.role, "content": m.content} for m in messages]
    finally:
        db.close()


def fetch_recent_messages(session_id: str, limit: int) -> list:
    db = SessionLocal()
    try:
        messages = db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.created_at.desc()).limit(limit).all()
        return [{"id": m.id, "role": m.role, "content": m.content} for m in reversed(messages)]
    finally:
        db.close()


def fetch_summary(session_id: str):
    db = SessionLocal()
    try:
        return db.query(ConversationSummary).filter(
            ConversationSummary.session_id == session_id
        ).first()
    finally:
        db.close()


def should_summarize(session_id: str) -> bool:
    db = SessionLocal()
    try:
        msg_count = db.query(Message).filter(Message.session_id == session_id).count()
        summary = db.query(ConversationSummary).filter(
            ConversationSummary.session_id == session_id
        ).first()

        if msg_count <= MAX_HISTORY:
            return False

        if summary is None:
            return msg_count >= SUMMARY_TRIGGER

        last_summary_msg_id = summary.up_to_msg_id
        new_msgs_since = db.query(Message).filter(
            Message.session_id == session_id,
            Message.id > last_summary_msg_id
        ).count()

        return new_msgs_since >= 4
    finally:
        db.close()


def generate_summary(session_id: str, existing_summary: str = None) -> tuple[str, int]:
    db = SessionLocal()
    try:
        if existing_summary is None:
            summary = db.query(ConversationSummary).filter(
                ConversationSummary.session_id == session_id
            ).first()
            existing_summary = summary.summary_text if summary else None

        msg_count = db.query(Message).filter(Message.session_id == session_id).count()
        limit = 8
        messages = db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.created_at.desc()).limit(limit).all()
        messages = list(reversed(messages))

        if messages:
            last_msg_id = messages[-1].id
        else:
            last_msg_id = 0

        history_text = "\n".join([
            f"[{m.role}]: {m.content[:300]}" for m in messages
        ])

        if existing_summary:
            prompt = [
                {"role": "system", "content": "You are a text summarizer."},
                {"role": "user", "content": f"""Previous conversation summary:
{existing_summary}

New recent messages to incorporate:
{history_text}

Update the summary to include the new messages while keeping it concise (3-5 sentences)."""}
            ]
        else:
            prompt = [
                {"role": "system", "content": "You are a text summarizer."},
                {"role": "user", "content": f"""Summarize this conversation in 3-5 sentences:

{history_text}"""}
            ]

        import asyncio
        loop = asyncio.new_event_loop()
        try:
            summary_text, _ = loop.run_until_complete(call_llm(prompt))
        finally:
            loop.close()

        return summary_text.strip(), last_msg_id
    finally:
        db.close()


def save_summary(session_id: str, summary_text: str, up_to_msg_id: int):
    db = SessionLocal()
    try:
        existing = db.query(ConversationSummary).filter(
            ConversationSummary.session_id == session_id
        ).first()

        if existing:
            existing.summary_text = summary_text
            existing.up_to_msg_id = up_to_msg_id
        else:
            new_summary = ConversationSummary(
                session_id=session_id,
                summary_text=summary_text,
                up_to_msg_id=up_to_msg_id
            )
            db.add(new_summary)

        db.commit()
    finally:
        db.close()


def build_conversation_context(session_id: str) -> list[dict]:
    message_count = count_messages(session_id)

    if message_count <= MAX_HISTORY:
        messages = fetch_all_messages(session_id)
        return format_as_chat_turns(messages)

    summary = fetch_summary(session_id)
    recent = fetch_recent_messages(session_id, limit=RECENT_AFTER_SUMMARY)

    context = []
    if summary:
        context.append({
            "role": "user",
            "content": f"[CONVERSATION SUMMARY SO FAR]\n{summary.summary_text}"
        })
        context.append({
            "role": "assistant",
            "content": "Understood, I have the context from our earlier conversation."
        })
    context.extend(format_as_chat_turns(recent))
    return context


def format_as_chat_turns(messages: list[dict]) -> list[dict]:
    formatted = []
    for m in messages:
        if m["role"] in ("user", "assistant"):
            formatted.append({"role": m["role"], "content": m["content"]})
    return formatted


def update_summary_if_needed(session_id: str):
    if should_summarize(session_id):
        summary = fetch_summary(session_id)
        existing_text = summary.summary_text if summary else None
        new_text, up_to_id = generate_summary(session_id, existing_text)
        save_summary(session_id, new_text, up_to_id)