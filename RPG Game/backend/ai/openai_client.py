import os
from google import genai

_client = None


def _api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = _api_key()
        if api_key:
            _client = genai.Client(api_key=api_key)
        else:
            _client = genai.Client()
    return _client


def has_api_key() -> bool:
    return bool(_api_key())
