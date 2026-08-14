from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.database import get_resume, init_db, save_resume
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