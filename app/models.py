from pydantic import BaseModel


class GapAnalysisResult(BaseModel):
    matched_keywords: list[str]
    missing_keywords: list[str]
    suggestions: str
