# FindBack

Campus lost-and-found application built with FastAPI and SQLite.

## Run locally

Install Python 3.12, then open a terminal in the project folder.

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

### Linux or macOS

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:8000 in your browser and create an account.

The application creates its local database automatically. No AWS account is needed to run locally. Press **Ctrl+C** in the terminal to stop the server.

If port 8000 is busy, add `--port 8002` to the run command and open http://127.0.0.1:8002 instead.
