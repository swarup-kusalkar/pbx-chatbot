import asyncio
import io
import json
import logging
import os
import re
import struct
import soundfile as sf
from typing import Optional

log = logging.getLogger(__name__)

_pipeline = None
_device = None


TTS_REPLACEMENTS = [
    (r'\bPBX\b', 'P. B. X.'),
    (r'\bPSTN\b', 'P. S. T. N.'),
    (r'\bDTMF\b', 'D. T. M. F.'),
    (r'\bIVR\b', 'I. V. R.'),
    (r'\bQoS\b', 'Q. O. S.'),
    (r'\b([0-9]+)\s*ms\b', r'\1 milliseconds'),
    (r'\b([0-9]+\.?[0-9]*)\s*MHz\b', r'\1 megahertz'),
    (r'\b([0-9]+\.?[0-9]*)\s*GHz\b', r'\1 gigahertz'),
]


def preprocess_for_tts(text: str) -> str:
    for pattern, replacement in TTS_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def load_model() -> None:
    global _pipeline, _device
    if _pipeline is not None:
        return

    try:
        import torch
        from kokoro import KPipeline
        from config import config

        _device = "cuda" if torch.cuda.is_available() else "cpu"
        log.info(f"Loading Kokoro TTS on {_device}")

        voice = os.getenv("VOICE_TTS_VOICE", "af_heart")

        hf_token = config.HUGGINGFACE_HUB_TOKEN or os.getenv("HUGGINGFACE_HUB_TOKEN")
        if hf_token:
            os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token
            log.info("Using HuggingFace token for model access")

        _pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
        _pipeline.load_voice(voice)

        if torch.cuda.is_available():
            vram = torch.cuda.memory_allocated() / 1024 / 1024
            log.info(f"Kokoro TTS loaded. VRAM: ~{vram:.0f}MB")
        else:
            log.info("Kokoro TTS loaded on CPU")

    except Exception as e:
        log.error(f"Failed to load Kokoro TTS: {e}")
        raise


def unload_model() -> None:
    global _pipeline
    if _pipeline is not None:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        _pipeline = None
        log.info("Kokoro TTS unloaded")


async def synthesize(text: str) -> bytes:
    if _pipeline is None:
        load_model()

    text = preprocess_for_tts(text)

    def _synthesize_sync() -> bytes:
        import torch
        voice = os.getenv("VOICE_TTS_VOICE", "af_heart")
        generator = _pipeline(text, voice=voice, speed=float(os.getenv("VOICE_TTS_SPEED", "1.0")))

        audio_chunks = []
        for _, _, audio in generator:
            audio_chunks.append(audio)

        if not audio_chunks:
            return b""

        import numpy as np
        full_audio = np.concatenate(audio_chunks)

        buf = io.BytesIO()
        sf.write(buf, full_audio, 24000, format='WAV', subtype='PCM_16')
        return buf.getvalue()

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _synthesize_sync)


def get_vram_usage_mb() -> float:
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / 1024 / 1024
    except Exception:
        pass
    return 0.0


VOICE_MAX_SENTENCE_BUFFER_WORDS = 4


def extract_sentence(buffer: str) -> Optional[str]:
    import re
    patterns = [
        (r'\.\s+', '. '),
        (r'\!\s+', '! '),
        (r'\?\s+', '? '),
        (r'\.\n', '.\n'),
        (r'\n', '\n'),
    ]
    for pattern, delimiter in patterns:
        match = re.search(pattern, buffer)
        if match:
            end = match.end()
            sentence = buffer[:end]
            words = sentence.split()
            if len(words) >= VOICE_MAX_SENTENCE_BUFFER_WORDS:
                return sentence
    return None


def build_audio_frame(wav_bytes: bytes, sentence_text: str) -> bytes:
    wav_len = struct.pack('>I', len(wav_bytes))
    meta = json.dumps({"t": sentence_text}).encode('utf-8')
    return b'\x01' + wav_len + wav_bytes + meta