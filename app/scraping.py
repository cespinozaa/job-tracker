import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; JobTrackerBot/1.0)"
REQUEST_TIMEOUT = 10
MIN_DESCRIPTION_LENGTH = 50


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
