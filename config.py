from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
    APP_PORT = int(os.getenv("APP_PORT", 3000))
    CHROMA_PERSIST_PATH = os.getenv("CHROMA_PERSIST_PATH", "./chroma_store")
    MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", 10))
    SUMMARY_TRIGGER_COUNT = int(os.getenv("SUMMARY_TRIGGER_COUNT", 10))
    RECENT_MESSAGES_AFTER_SUMMARY = int(os.getenv("RECENT_MESSAGES_AFTER_SUMMARY", 6))

    # Voice mode config
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    NVIDIA_NIM_BASE_URL = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    NVIDIA_NIM_MODEL = os.getenv("NVIDIA_NIM_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
    HUGGINGFACE_HUB_TOKEN = os.getenv("HUGGINGFACE_HUB_TOKEN")

    # Voice thresholds (used in code)
    VOICE_MIN_UTTERANCE_SAMPLES = int(os.getenv("VOICE_MIN_UTTERANCE_SAMPLES", "8000"))
    VOICE_TTS_VOICE = os.getenv("VOICE_TTS_VOICE", "af_heart")
    VOICE_TTS_DEVICE = os.getenv("VOICE_TTS_DEVICE", "cuda")
    VOICE_TTS_SPEED = float(os.getenv("VOICE_TTS_SPEED", "1.0"))

config = Config()