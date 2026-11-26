# FindBack

Campus lost-and-found application built with FastAPI and SQLite.

## Live application

FindBack is deployed on AWS EC2 with HTTPS: **[Open FindBack](https://3.145.182.56/)**.

Create an account or sign in to browse reports. The demo is available while the EC2 instance is running. Its address may change after the instance is stopped and started.

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

## Documentation

- [System architecture](docs/architecture.md)
- [AWS deployment and operations](docs/deployment.md)
- [API documentation](docs/api.md)
- [Testing and verification](docs/verification.md)
- [Project status and future work](docs/progress.md)
