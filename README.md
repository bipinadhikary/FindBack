# FindBack

Campus lost-and-found platform built with FastAPI and SQLite. Requires Python 3.14.

## Windows (PowerShell or CMD)

Run from the project folder. Skip environment creation if `.venv` already exists.

```text
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

## macOS

```sh
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:8000. Press **Ctrl+C** to stop.

If port 8000 is occupied, add `--port 8001` to the launch command and open http://127.0.0.1:8001.

The SQLite database is created automatically at `data/findback.sqlite3` on first startup.

## Documentation

- [API and validation](docs/api.md)
- [Architecture](docs/architecture.md)
- [Progress and remaining work](docs/progress.md)
- [Verification](docs/verification.md)
- [Demo walkthrough](docs/demo-script.md)
- [Presentation outline](docs/midpoint-outline.md)
- [Presentation evidence](docs/presentation-evidence.md)
- [S3 backup experiment - deferred](docs/cloud-backup.md)
