from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.charts import build_status_flow
from app.database import (
    STATUS_LABELS,
    VALID_STATUSES,
    create_application,
    get_application,
    get_applications,
    get_gap_analyses,
    get_resume,
    init_db,
    save_gap_analysis,
    save_resume,
    update_application,
    update_application_status,
)
from app.gap_analysis import GapAnalysisError, run_gap_analysis
from app.parsing import parse_resume_file
from app.scraping import ScrapeError, scrape_job_posting

BASE_DIR = Path(__file__).parent

app = FastAPI(title="Job Application Tracker")

templates = Jinja2Templates(directory=BASE_DIR / "templates")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def render(request: Request, template_name: str, active_nav: str, **context):
    """Renders a template with the sidebar context (resume status, active nav
    item) every page needs, so routes don't each have to wire it up."""
    return templates.TemplateResponse(
        template_name,
        {
            "request": request,
            "active_nav": active_nav,
            "resume": get_resume(),
            "status_labels": STATUS_LABELS,
            **context,
        },
    )


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health_check():
    return {"status": "ok"}


def _safe_redirect(url: str, default: str = "/") -> str:
    """Only allow redirecting to a local path, never an external URL."""
    if url.startswith("/") and not url.startswith("//"):
        return url
    return default


@app.get("/")
def list_applications(request: Request, status: str | None = None):
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(400, "Invalid status filter")

    all_applications = get_applications()
    status_counts = {s: 0 for s in VALID_STATUSES}
    for application in all_applications:
        status_counts[application["status"]] += 1

    applications = (
        [a for a in all_applications if a["status"] == status]
        if status
        else all_applications
    )
    awaiting_count = status_counts["applied"] + status_counts["interviewing"]
    flow = build_status_flow(status_counts, STATUS_LABELS)

    return render(
        request,
        "index.html",
        "list",
        applications=applications,
        statuses=VALID_STATUSES,
        selected_status=status,
        status_counts=status_counts,
        total_count=len(all_applications),
        awaiting_count=awaiting_count,
        flow=flow,
        wide_layout=True,
    )


@app.post("/applications/{application_id}/status")
def update_status_route(
    application_id: int, status: str = Form(...), redirect_to: str = Form("/")
):
    if get_application(application_id) is None:
        raise HTTPException(404, "Application not found")
    if status not in VALID_STATUSES:
        raise HTTPException(400, "Invalid status")

    update_application_status(application_id, status)
    return RedirectResponse(url=_safe_redirect(redirect_to), status_code=303)


@app.get("/applications/new")
def new_application_form(request: Request):
    return render(request, "new_application.html", "new")


@app.post("/applications/new/scrape")
def scrape_application_url(request: Request, url: str = Form(...)):
    try:
        scraped = scrape_job_posting(url)
    except ScrapeError as exc:
        return render(request, "new_application.html", "new", url=url, error=str(exc))
    return render(
        request,
        "new_application.html",
        "new",
        url=url,
        company=scraped["company"],
        title=scraped["title"],
        job_description=scraped["job_description"],
        scraped=True,
    )


@app.post("/applications/new")
def submit_new_application(
    company: str = Form(...),
    title: str = Form(...),
    job_description: str = Form(...),
    url: str = Form(""),
    notes: str = Form(""),
):
    application_id = create_application(
        company, title, job_description, url or None, notes or None
    )
    return RedirectResponse(url=f"/applications/{application_id}", status_code=303)


@app.get("/applications/{application_id}")
def application_detail(request: Request, application_id: int):
    application = get_application(application_id)
    if application is None:
        raise HTTPException(404, "Application not found")
    gap_analyses = get_gap_analyses(application_id)
    return render(
        request,
        "application_detail.html",
        "list",
        application=application,
        statuses=VALID_STATUSES,
        gap_analyses=gap_analyses,
    )


@app.post("/applications/{application_id}/analyze")
def analyze_application(request: Request, application_id: int):
    application = get_application(application_id)
    if application is None:
        raise HTTPException(404, "Application not found")

    resume = get_resume()
    if resume is None:
        raise HTTPException(400, "Upload a resume before running gap analysis.")

    try:
        result = run_gap_analysis(resume["raw_text"], application["job_description"])
    except GapAnalysisError as exc:
        gap_analyses = get_gap_analyses(application_id)
        return render(
            request,
            "application_detail.html",
            "list",
            application=application,
            statuses=VALID_STATUSES,
            gap_analyses=gap_analyses,
            analysis_error=str(exc),
        )

    save_gap_analysis(
        application_id,
        result.matched_keywords,
        result.missing_keywords,
        result.suggestions,
    )
    return RedirectResponse(url=f"/applications/{application_id}", status_code=303)


@app.post("/applications/{application_id}/update")
def update_application_route(
    application_id: int,
    status: str = Form(...),
    notes: str = Form(""),
):
    if get_application(application_id) is None:
        raise HTTPException(404, "Application not found")
    if status not in VALID_STATUSES:
        raise HTTPException(400, "Invalid status")

    update_application(application_id, status, notes or None)
    return RedirectResponse(url=f"/applications/{application_id}", status_code=303)


@app.get("/resume")
def resume_page(request: Request):
    return render(request, "resume.html", "resume")


@app.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(400, "Only PDF and DOCX files are supported.")

    file_bytes = await file.read()
    raw_text = parse_resume_file(file.filename, file_bytes)

    if not raw_text.strip():
        raise HTTPException(400, "Couldn't extract any text from that file.")

    save_resume(file.filename, raw_text)
    return RedirectResponse(url="/resume", status_code=303)
