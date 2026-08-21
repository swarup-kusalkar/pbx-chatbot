import asyncio
import base64
import json
import logging
import os
import struct
import httpx
from typing import AsyncGenerator, List, Optional

from config import config

log = logging.getLogger(__name__)

NVIDIA_API_KEY = config.NVIDIA_API_KEY
NVIDIA_NIM_BASE_URL = config.NVIDIA_NIM_BASE_URL
NVIDIA_NIM_MODEL = config.NVIDIA_NIM_MODEL

API_URL = f"{NVIDIA_NIM_BASE_URL}/chat/completions"

SYSTEM_PROMPT = """You are a PBX technical support assistant. You speak responses that will be converted
to audio — keep answers conversational, avoid markdown, bullet points, or special
characters. Do not use asterisks, hyphens as list markers, pound signs, or any
formatting that sounds wrong when read aloud.

When the user sends an audio message, you MUST follow this exact format:
Line 1: [heard: <exact verbatim transcript of what the user said>]
Line 2 onwards: Your response in plain, spoken English.

Do NOT add any text before the [heard:] line.
Do NOT include the [heard:] line in your spoken response — it is metadata only.
Keep responses under 150 words unless the question genuinely requires more detail.
Answer only from the context provided. If the context does not contain the answer,
say: "I don't have that information in the knowledge base. Can you check the PBX
manual or contact your administrator?"""


class NIMUnavailableError(Exception):
    pass


class NIMParseError(Exception):
    pass


def pcm_int16_to_wav(pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = len(pcm_bytes)

    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_size,
        b'WAVE',
        b'fmt ',
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b'data',
        data_size
    )
    return header + pcm_bytes


def peak_normalize_wav(wav_bytes: bytes) -> bytes:
    if len(wav_bytes) < 44:
        return wav_bytes

    header = wav_bytes[:44]
    pcm_data = wav_bytes[44:]

    import array
    samples = array.array('h', pcm_data)
    if not samples:
        return wav_bytes

    max_val = max(abs(s) for s in samples)
    if max_val == 0:
        return wav_bytes

    target_peak = int(32767 * 0.707)
    scale = target_peak / max_val
    if scale >= 1.0:
        return wav_bytes

    normalized = array.array('h', (int(s * scale) for s in samples))
    return header + normalized.tobytes()


async def call_nemotron(
    wav_bytes: bytes,
    rag_chunks: List[str],
    conversation_history: List[dict],
    interrupted_partial: Optional[str],
    cancel_event: asyncio.Event,
) -> AsyncGenerator[tuple[str, str], None]:
    """
    Yields:
      ("heard", "<transcript>")        — exactly once, from [heard:] line
      ("token", "<text>")              — many times, the response tokens
    Raises:
      NIMUnavailableError              — on 429 or 5xx
      NIMParseError                    — if [heard:] line format fails and fallback needed
    """
    wav_b64 = base64.b64encode(wav_bytes).decode()

    rag_context = "KNOWLEDGE BASE CONTEXT:\n"
    for chunk in rag_chunks:
        rag_context += f"---\n{chunk.strip()}\n"
    rag_context += "---\n\n"

    if interrupted_partial:
        rag_context += f"NOTE: In your previous response you said '{interrupted_partial}' before being interrupted. The user has now asked a new question. Do not re-answer the previous question unless asked.\n\n"

    rag_context += "Answer the user's spoken question using the knowledge base context above."

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for hist in conversation_history:
        messages.append(hist)

    user_content = [
        {
            "type": "audio_url",
            "audio_url": {"url": f"data:audio/wav;base64,{wav_b64}"}
        },
        {"type": "text", "text": rag_context}
    ]
    messages.append({"role": "user", "content": user_content})

    payload = {
        "model": NVIDIA_NIM_MODEL,
        "messages": messages,
        "max_tokens": 512,
        "reasoning_budget": 0,
        "stream": True,
        "temperature": 0.4,
        "top_p": 0.9,
    }

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }

    log.info(f"Calling Nemotron NIM API with {len(rag_chunks)} RAG chunks, {len(conversation_history)} history messages")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            async with client.stream("POST", API_URL, json=payload, headers=headers) as response:
                if response.status_code == 429:
                    raise NIMUnavailableError("Rate limited (429)")
                if response.status_code >= 500:
                    raise NIMUnavailableError(f"Server error ({response.status_code})")
                response.raise_for_status()

                heard_emitted = False
                buffer = ""

                async for line in response.aiter_lines():
                    if cancel_event.is_set():
                        log.info("Cancel event set, stopping Nemotron stream")
                        break

                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if "choices" in chunk and chunk["choices"]:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                token = delta["content"]
                                buffer += token

                                if not heard_emitted and "\n" in buffer:
                                    first_line = buffer.split("\n")[0].strip()
                                    if first_line.startswith("[heard:"):
                                        transcript = first_line[7:-1] if first_line.endswith("]") else first_line[7:]
                                        heard_emitted = True
                                        yield ("heard", transcript)
                                        buffer = buffer[len(first_line)+1:]
                                    else:
                                        heard_emitted = True
                                        raise NIMParseError(f"Expected [heard:] line, got: {first_line[:100]}")

                                if heard_emitted:
                                    yield ("token", token)

                    except json.JSONDecodeError:
                        continue

                if not heard_emitted:
                    raise NIMParseError("Stream ended without [heard:] line")

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 500, 502, 503, 504):
                raise NIMUnavailableError(f"HTTP {e.response.status_code}")
            raise