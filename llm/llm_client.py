import httpx
from config import config

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"


class LLMUnavailableError(Exception):
    pass


async def _call_groq(messages: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {config.GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": config.GROQ_MODEL,
                "messages": messages,
                "max_tokens": 600,
                "temperature": 0.3
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def _call_gemini(messages: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{GEMINI_URL}?key={config.GEMINI_API_KEY}",
            headers={
                "Content-Type": "application/json"
            },
            json={
                "model": config.GEMINI_MODEL,
                "messages": messages,
                "max_tokens": 600,
                "temperature": 0.3
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def call_llm(messages: list[dict]) -> tuple[str, str]:
    try:
        reply = await _call_groq(messages)
        return reply, "groq"
    except Exception as groq_error:
        try:
            reply = await _call_gemini(messages)
            return reply, "gemini"
        except Exception as gemini_error:
            raise LLMUnavailableError(
                f"Both LLMs failed. Groq: {groq_error}. Gemini: {gemini_error}"
            )