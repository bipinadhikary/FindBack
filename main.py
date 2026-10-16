"""FindBack's local report API, SQLite storage, and static web interface."""

from contextlib import asynccontextmanager, contextmanager
from datetime import date
import os
from pathlib import Path
import sqlite3
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(
    os.environ.get("FINDBACK_DB_PATH", str(ROOT / "data" / "findback.sqlite3"))
)


@contextmanager
def connect():
    """Commit successful operations and always close the request's connection."""
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


@asynccontextmanager
async def lifespan(app):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                report_type TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open'
            )
        """)
    yield


app = FastAPI(
    title="FindBack",
    description="AI-assisted campus lost-and-found platform",
    version="0.1.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


class ReportCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    report_type: Literal["lost", "found"]
    title: str = Field(min_length=3, max_length=100)
    category: Literal["backpack", "water bottle", "headphones"]
    description: str = Field(min_length=10, max_length=2000)
    location: str = Field(min_length=2, max_length=200)
    date: date

    @field_validator("date")
    @classmethod
    def validate_date(cls, value):
        if value > date.today():
            raise ValueError("Date cannot be in the future")
        return value


class Report(ReportCreate):
    id: str
    status: Literal["open", "resolved"] = "open"


@app.get("/")
def home():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reports", response_model=Report, status_code=201)
def create_report(data: ReportCreate):
    report = Report(id=str(uuid4()), **data.model_dump())
    values = report.model_dump(mode="json")
    with connect() as db:
        db.execute("""
            INSERT INTO reports (
                id, report_type, title, category, description, location, date, status
            ) VALUES (
                :id, :report_type, :title, :category, :description, :location, :date, :status
            )
        """, values)
    return report


@app.get("/reports", response_model=list[Report])
def list_reports(
    report_type: Literal["lost", "found"] | None = None,
    category: Literal["backpack", "water bottle", "headphones"] | None = None,
    q: str = Query(default="", max_length=200),
):
    clauses, params = [], []
    for column, value in (("report_type", report_type), ("category", category)):
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    if q.strip():
        clauses.append(
            "instr(lower(title || ' ' || description || ' ' || location), lower(?)) > 0"
        )
        params.append(q.strip())
    sql = "SELECT * FROM reports"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    with connect() as db:
        rows = db.execute(sql + " ORDER BY date DESC, rowid DESC", params)
        return [dict(row) for row in rows]


@app.get("/reports/{report_id}", response_model=Report)
def get_report(report_id: str):
    with connect() as db:
        row = db.execute(
            "SELECT * FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return dict(row)
