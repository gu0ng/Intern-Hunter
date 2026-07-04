from fastapi import FastAPI

from app.api import routes_applications, routes_interview, routes_jobs, routes_match, routes_resume
from app.db.database import init_db


app = FastAPI(title="Intern-Hunter", version="0.2.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(routes_resume.router)
app.include_router(routes_jobs.router)
app.include_router(routes_match.router)
app.include_router(routes_interview.router)
app.include_router(routes_applications.router)
