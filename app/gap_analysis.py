from google.genai import errors, types
from pydantic import ValidationError

from app.llm import LLMError, get_client
from app.models import GapAnalysisResult

MODEL = "gemini-3.5-flash-lite"


class GapAnalysisError(Exception):
    """Raised when gap analysis can't be completed, so the caller can show a clean error."""


def run_gap_analysis(resume_text: str, job_description: str) -> GapAnalysisResult:
    try:
        client = get_client()
    except LLMError as exc:
        raise GapAnalysisError(str(exc)) from exc

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
