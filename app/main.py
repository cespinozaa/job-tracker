from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.database import (
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


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def list_applications(request: Request):
    applications = get_applications()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "applications": applications, "statuses": VALID_STATUSES},
    )


@app.post("/applications/{application_id}/status")
def update_status_route(application_id: int, status: str = Form(...)):
    if get_application(application_id) is None:
        raise HTTPException(404, "Application not found")
    if status not in VALID_STATUSES:
        raise HTTPException(400, "Invalid status")

    update_application_status(application_id, status)
    return RedirectResponse(url="/", status_code=303)


@app.get("/applications/new")
def new_application_form(request: Request):
    return templates.TemplateResponse("new_application.html", {"request": request})


@app.post("/applications/new/scrape")
def scrape_application_url(request: Request, url: str = Form(...)):
    try:
        scraped = scrape_job_posting(url)
    except ScrapeError as exc:
        return templates.TemplateResponse(
            "new_application.html",
            {"request": request, "url": url, "error": str(exc)},
        )
    return templates.TemplateResponse(
        "new_application.html",
        {
            "request": request,
            "url": url,
            "company": scraped["company"],
            "title": scraped["title"],
            "job_description": scraped["job_description"],
            "scraped": True,
        },
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
    return templates.TemplateResponse(
        "application_detail.html",
        {
            "request": request,
            "application": application,
            "statuses": VALID_STATUSES,
            "gap_analyses": gap_analyses,
        },
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
        return templates.TemplateResponse(
            "application_detail.html",
            {
                "request": request,
                "application": application,
                "statuses": VALID_STATUSES,
                "gap_analyses": gap_analyses,
                "analysis_error": str(exc),
            },
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
    resume = get_resume()
    return templates.TemplateResponse(
        "resume.html", {"request": request, "resume": resume}
    )


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