import requests
from bs4 import BeautifulSoup
from google.genai import errors

from app.llm import LLMError, get_client

USER_AGENT = "Mozilla/5.0 (compatible; JobTrackerBot/1.0)"
REQUEST_TIMEOUT = 10
MIN_DESCRIPTION_LENGTH = 50

UNAVAILABLE_PHRASES = [
    "no longer available",
    "posting has expired",
    "position has been filled",
    "job has been closed",
    "no longer accepting applications",
    "this job is no longer",
]

CLEANUP_MODEL = "gemini-3.5-flash-lite"

CLEANUP_PROMPT = (
    "The following text was scraped from a job posting webpage. It may mix "
    "generic company boilerplate (About Us, EEO statements, hiring process "
    "overviews, legal notices) in with the actual role description. Return only "
    "the parts relevant to the role itself: the job description, "
    "responsibilities, and qualifications/requirements. Preserve the original "
    "wording exactly — remove irrelevant sections, don't summarize or rephrase "
    "what you keep. If nothing looks removable, return the text unchanged, with "
    "no extra commentary.\n\nSCRAPED TEXT:\n{text}"
)


class ScrapeError(Exception):
    """Raised when a posting can't be scraped, so the caller can fall back to manual paste."""


def scrape_job_posting(url: str) -> dict:
    try:
        response = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise ScrapeError("That request timed out.") from exc
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        raise ScrapeError(f"The site returned an error (HTTP {status}).") from exc
    except requests.exceptions.RequestException as exc:
        raise ScrapeError("Couldn't reach that URL.") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    description = _extract_description(soup)
    if len(description) < MIN_DESCRIPTION_LENGTH:
        raise ScrapeError("Couldn't find usable job description content on this page.")
    if _looks_unavailable(description):
        raise ScrapeError("This posting looks like it's no longer available.")

    return {
        "title": _extract_title(soup),
        "company": _extract_company(soup),
        "job_description": description,
    }


def _meta_content(soup: BeautifulSoup, property_name: str) -> str | None:
    tag = soup.find("meta", property=property_name) or soup.find(
        "meta", attrs={"name": property_name}
    )
    return tag["content"].strip() if tag and tag.get("content") else None


def _extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    return (
        _meta_content(soup, "og:title")
        or (h1.get_text(strip=True) if h1 else None)
        or (soup.title.get_text(strip=True) if soup.title else None)
        or ""
    )


def _extract_company(soup: BeautifulSoup) -> str:
    return _meta_content(soup, "og:site_name") or ""


def _extract_description(soup: BeautifulSoup) -> str:
    candidate = soup.find("article") or soup.find("main") or soup.find("body")
    if candidate is None:
        return ""
    text = candidate.get_text(separator="\n", strip=True)
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _looks_unavailable(description: str) -> bool:
    lowered = description.lower()
    return any(phrase in lowered for phrase in UNAVAILABLE_PHRASES)


def clean_job_description(raw_text: str) -> str:
    """
    Uses the LLM to strip company boilerplate from scraped posting text.
    Falls back to the raw text (no error raised) if no API key is configured
    or the request fails, so scraping keeps working without an LLM available.
    """
    try:
        client = get_client()
    except LLMError:
        return raw_text

    try:
        response = client.models.generate_content(
            model=CLEANUP_MODEL,
            contents=CLEANUP_PROMPT.format(text=raw_text),
        )
    except errors.APIError:
        return raw_text

    cleaned = response.text.strip() if response.text else ""
    return cleaned or raw_text
