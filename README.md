# FindBack

A campus lost-and-found course prototype by **Bipin Adhikari**, sole developer, **Group 32**.

The midpoint prototype runs locally: FastAPI serves a web interface and stores reports in SQLite. Initial scope is one campus and three categories: backpacks, water bottles, and headphones. Cloud integration and AI matching remain planned.

## Quick start: Windows PowerShell or CMD

From the project folder, create an environment only if `.venv` does not exist:

```text
cd C:\Users\Bipin\Projects\findback
py -3.14 -m venv .venv
```

Install dependencies and start the application. These commands use the environment directly and work in both PowerShell and CMD:

```text
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Open http://127.0.0.1:8000. API documentation is at http://127.0.0.1:8000/docs. The launcher prints both links. Stop with **Ctrl+C**. If port 8000 is occupied:

```text
.\.venv\Scripts\python.exe run.py --port 8001
```

Then use http://127.0.0.1:8001. No activation is needed. For manual activation, CMD uses `.venv\Scripts\activate.bat`; PowerShell uses `.\.venv\Scripts\Activate.ps1` if execution policy permits. Verified interpreter: Python 3.14.7.

## Mac setup

Create a separate environment; do not copy the Windows `.venv`:

```sh
cd /path/to/findback
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

The equivalent direct Uvicorn command is `python -m uvicorn main:app --host 127.0.0.1 --port 8000`. Keep the prototype bound to localhost.

## Implemented features

- Create lost and found reports with validated text, category, location, and date.
- Browse reports and combine type/category filters with a text search.
- View individual details, including report ID and open status.
- Preserve reports across server restarts in SQLite.
- Use a static HTML/CSS/JavaScript interface without a frontend build step.
- Use parameterized SQL and render report content as text rather than HTML.

### Storage

Startup creates `data/findback.sqlite3` relative to the source directory. Each startup reuses that file. `FINDBACK_DB_PATH` optionally overrides the path for isolated tests. Local data is excluded from Git; a fresh clone starts with no reports. Use synthetic demo reports only.

To inspect the database from the project folder on Windows:

```text
.\.venv\Scripts\python.exe -m sqlite3 data\findback.sqlite3
```

Then enter `SELECT * FROM reports;` or `PRAGMA table_info(reports);`. Type `.quit` to exit.

### API

| Method | Path | Behavior |
|---|---|---|
| GET | `/` | Web interface |
| GET | `/health` | Process health; does not check the database |
| POST | `/reports` | Create a report; returns 201 |
| GET | `/reports` | List; optional `report_type`, `category`, and `q` filters |
| GET | `/reports/{report_id}` | Report details or 404 |
| GET | `/docs` | Interactive API documentation |

Example synthetic POST body:

```json
{
  "report_type": "lost",
  "title": "Demo blue backpack",
  "category": "backpack",
  "description": "Blue demo backpack with a yellow star",
  "location": "Demo library",
  "date": "2026-10-12"
}
```

Types: `lost`, `found`. Categories: `backpack`, `water bottle`, `headphones`. Text is trimmed. Title length is 3-100 characters; description 10-2000; location 2-200. Dates must be valid and no later than the server's local date. Invalid/missing body fields, extra body fields, and unsupported filter values return 422. Lists sort by event date descending, then insertion order descending. Search covers title, description, and location using SQLite's case mapping.

## Verification

Windows, without activating the environment:

```text
.\.venv\Scripts\python.exe scripts\verify.py
```

Mac, with the environment active: `python scripts/verify.py`.

The script starts a real server on an available localhost port, checks creation/listing/details/filters/validation/404 responses and frontend assets, then restarts the process and confirms both reports remain. It uses a temporary database and does not change demo data. See [verification evidence](docs/verification.md).

## Project structure

```text
main.py                    FastAPI routes, models, and SQLite persistence
run.py                     Local launcher with browser links
requirements.txt           Pinned local runtime dependencies
static/                    HTML, CSS, and browser JavaScript
scripts/verify.py          HTTP workflow and restart verification
docs/                      Architecture, progress, presentation notes, demo script
scripts/cloud_backup.py    Deferred S3 experiment (not part of the running app)
scripts/test_cloud_backup.py  Offline checks for the S3 experiment
requirements-cloud.txt     Optional experiment dependencies
```

## Midpoint materials

- [Current and proposed architecture](docs/architecture.md)
- [Progress and remaining milestones](docs/progress.md)
- [Six-slide presentation content and speaker notes](docs/midpoint-outline.md)
- [Five-to-ten-minute demo script](docs/demo-script.md)
- [Presentation evidence index](docs/presentation-evidence.md)

The PowerPoint and screenshots are separate submission materials and are not bundled in this checkout.

## Limitations and next steps

This is a local prototype. There is no authentication, ownership verification, editing/resolution workflow, photo upload, implemented matching, verified AWS integration, notifications, or CI/CD. All reports remain open. Pagination, migrations, automated backups, monitoring, and abuse controls are not implemented.

The [optional S3 backup experiment](docs/cloud-backup.md) is retained for a later milestone. Local export and offline checks pass; a live AWS upload/download has not been verified. It is not required to run FindBack.

Next: finish the midpoint recording/repository submission, resolve Learner Lab access and verify a cloud feature, then develop identity/recovery controls, private photos, and preliminary matching. Semantic matching remains planned.
