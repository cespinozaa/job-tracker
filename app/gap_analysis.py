import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from app.models import GapAnalysisResult

load_dotenv()

MODEL = "gemini-3.5-flash-lite"

_client: genai.Client | None = None


class GapAnalysisError(Exception):
    """Raised when gap analysis can't be completed, so the caller can show a clean error."""


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise GapAnalysisError(
                "GEMINI_API_KEY is not set. Add it to a .env file in the project root."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def run_gap_analysis(resume_text: str, job_description: str) -> GapAnalysisResult:
    client = _get_client()

    prompt = (
        "Compare this resume against this job posting. Identify which of "
        "the posting's key skills/requirements are evidenced in the resume "
        "(matched) and which are not (missing), then give a short paragraph "
        "of suggestions for tailoring the resume to this posting.\n\n"
        f"RESUME:\n{resume_text}\n\nJOB POSTING:\n{job_description}"
    )

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GapAnalysisResult,
            ),
        )
    except errors.APIError as exc:
        raise GapAnalysisError(f"The gap analysis request failed: {exc}") from exc

    parsed = response.parsed
    if parsed is None:
        raise GapAnalysisError("The model didn't return a structured result.")
    if isinstance(parsed, GapAnalysisResult):
        return parsed

    try:
        return GapAnalysisResult.model_validate(parsed)
    except ValidationError as exc:
        raise GapAnalysisError(f"Got a malformed result from the model: {exc}") from exc
