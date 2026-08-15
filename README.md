# Job Application Tracker (Docket) 📋

## Intro ✨

This is a local-first web app I built to stop losing track of my job search across a dozen browser tabs and a half-updated spreadsheet. It tracks every application in one place, can pull the title/company/description straight from a posting URL, and uses an LLM to compare a job posting against my resume so I know how to tailor it before I apply. The LLM shows a 'gap analysis' meaning which job keywords my resume already has, which ones its missing, as well as a short paragraph with advice on what to focus on when tailoring my resume. It's designed to run on my own machine, not to be deployed publicly as there's no login system, no hosting, just a local SQLite file.

The project is branded "Docket" internally (a docket being, literally, a list of matters to track), though the project itself is just called the Job Application Tracker.

## Images

<img src="https://github.com/user-attachments/assets/caba0e8c-ec3a-41e4-912f-051dd1d59920" width="750">

<img src="https://github.com/user-attachments/assets/71083e94-6109-4ae3-a7bb-8b6855453050" width="750">

<img src="https://github.com/user-attachments/assets/67ac53e9-a390-4252-857c-ef497ebfbf0a" width="750">




## Tech Stack ⚙️

- Python
- FastAPI
- SQLite (raw `sqlite3`, no ORM)
- Jinja2
- Pydantic
- Uvicorn
- `requests` + BeautifulSoup4
- `pdfplumber` + `python-docx`
- Google Gemini API (`google-genai`)
- `python-dotenv`
- Vanilla HTML/CSS (no frontend framework)
- Self-hosted webfonts (Fraunces, Manrope)

## Features ⚗️

1. **Applications dashboard**: every application as a card containing company, title, status, and date, with status filter pills and a Pipeline Overview chart (a small Sankey-style flow diagram, hand-built as inline SVG) showing the current distribution across the pipeline at a glance.
2. **Add an application** two ways: paste a job posting URL and the app scrapes title/company/description (falling back cleanly to manual paste if a site blocks scraping or the posting's expired), or just paste the details in yourself. Scraped descriptions are run through the LLM to strip company boilerplate (About Us blurbs, EEO statements, legal notices) down to the actual role description.
3. **Application detail page**: company, title, description, status, and notes are all editable in place; status also has a quick-edit dropdown right from the dashboard. Applications can be deleted.
4. **Status pipeline**: seven stages — Applied → Completed OA → Interviewing → Waiting to Hear Back → Offer / Rejected / Ghosted, each with its own color.
5. **Resume upload**: PDF or DOCX, parsed to plain text with a preview so I can confirm parsing didn't mess up anything. Only the latest resume is kept.
6. **Gap analysis**: one click sends the resume and a posting to Gemini and gets back matched keywords, missing keywords, and a short paragraph of tailoring suggestions. Every run is kept, so I can see how the gap changes as I tailor my resume.
7. **Light and dark mode**, automatically following your OS/browser preference so every color token, including all seven status colors, is defined for both. No in-app toggle yet, just system-preference detection.
8. **Responsive layout**: the sidebar collapses to a top bar and the two-column dashboard stacks to one column on narrow screens.

## Process 🫧

I built this following spec-driven development, outlining specific milestones. I started by writing out a full spec (data model, user flows, tech choices, and explicitly what was _out_ of scope) before any code existed, then worked through it as seven ordered milestones, each on its own git branch: scaffolding → resume upload → add application → status updates → URL scraping → gap analysis → polish.

A few decisions along the way ended up mattering more than expected. I originally planned gap analysis around the Anthropic API, but hit a billing wall mid-build — rather than block on that, I swapped to Gemini's free tier and rebuilding the structured-output call around `response_schema` instead of tool-use. Scraping needed real-world testing to find its actual limits: a plain `requests` + BeautifulSoup scrape works fine on simple pages, but sites like LinkedIn and certain careers portal pages (Phenom People-based, with what looks like bot detection) serve a decoy page instead of the real posting, which is why the scrape flow always drops into an editable review step before saving, and why I later added a check for "no longer available" boilerplate so that decoy content fails cleanly instead of silently looking like a successful scrape.

The frontend design was inspired by a couple websites, taking certain aspects like use of white space, borders, color palette to inform the design, with real webfonts (Fraunces + Manrope, self-hosted since the mockup environment blocks font CDNs). Every feature was tested end-to-end against a real running server (creating applications, editing them, running actual Gemini API calls, deleting an application that had gap-analysis history to specifically check the foreign-key cleanup).

## Learnings 📖

- **Spec-first development**: writing out the data model, user flows, and explicit non-goals before any code existed made every later milestone faster to build and easier to review.
- **FastAPI + Pydantic**: got hands-on with FastAPI's automatic request validation and Jinja2 templating, and saw a concrete case for Pydantic beyond "type hints", validating the LLM's structured JSON output before it ever touches the database.
- **Real-world scraping limits**: the honest failure modes of scraping aren't just "the site is down", it includes login walls, bot detection, and JS-rendered content all produce a page that _looks_ successfully fetched. Designing around that (always review before save) mattered more than trying to solve scraping perfectly.
- **Git workflow discipline**: one feature branch and one PR per milestone made it easy to write an accurate PR description and to actually see the diff before merging.

## How can this project be improved? 🛠️

- **Making it publicly available**: Scaling the application to allow for multiple users, allowing account creation, deploying & hosting online so anyone can use it
- **Follow-up reminders**: flag applications that have gone quiet for N days without an update, this was deliberately left out of v1 to keep scope tight, but a natural next step.
- **Resume version history**: right now only the latest resume is kept; keeping past versions would let old gap-analysis runs stay meaningful even after a resume rewrite.
- **A unified daily brief**: this app was designed so a future script could read `job_tracker.db` directly (it's just a SQLite file) without the server running, with the idea being a single dashboard that pulls from this and a few other personal tracking tools at once.
- **Auto-fill applications**: out of scope by choice since most job sites actively resist this, and it edges toward automating away information a real applicant should be entering deliberately.

## Running The Project 🪄

**Requirements**: Python 3.11+, and a free [Gemini API key](https://aistudio.google.com/apikey) if you want gap analysis to work (everything else runs without one).

```bash
# 1. Clone the repo
git clone https://github.com/cespinozaa/job-tracker.git
cd job-tracker

# 2. Create a virtual environment
python -m venv .venv        # macOS/Linux: python3 -m venv .venv

# 3. Activate it
.venv\Scripts\Activate.ps1  # Windows (PowerShell)
source .venv/bin/activate   # macOS/Linux

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the server
python -m uvicorn app.main:app --reload
```

Then create a `.env` file in the project root with your Gemini key:

```
GEMINI_API_KEY=your-key-here
```

Open **http://localhost:8000** in your browser. A `job_tracker.db` SQLite file is created automatically on first run, nothing else to set up.
