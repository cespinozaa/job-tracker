import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

_client: genai.Client | None = None


class LLMError(Exception):
    """Raised when no LLM client is available, e.g. a missing API key."""


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise LLMError(
                "GEMINI_API_KEY is not set. Add it to a .env file in the project root."
            )
        _client = genai.Client(api_key=api_key)
    return _client
