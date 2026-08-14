from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.database import (
    create_application,
    get_application,
    get_applications,
    get_resume,
    init_db,
    save_resume,
)
from app.parsing import parse_resume_file

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
        "index.html", {"request": request, "applications": applications}
    )


@app.get("/applications/new")
def new_application_form(request: Request):
    return templates.TemplateResponse("new_application.html", {"request": request})


@app.post("/applications/new")
def submit_new_application(
    company: str = Form(...),
    title: str = Form(...),
    job_description: str = Form(...),
    notes: str = Form(""),
):
    application_id = create_application(company, title, job_description, notes or None)
    return RedirectResponse(url=f"/applications/{application_id}", status_code=303)


@app.get("/applications/{application_id}")
def application_detail(request: Request, application_id: int):
    application = get_application(application_id)
    if application is None:
        raise HTTPException(404, "Application not found")
    return templates.TemplateResponse(
        "application_detail.html", {"request": request, "application": application}
    )


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