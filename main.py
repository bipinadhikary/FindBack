from fastapi import FastAPI

app = FastAPI(
    title="FindBack",
    description="Campus lost-and-found platform",
    version="0.1.0",
)


@app.get("/")
def home():
    return {"message": "Welcome to FindBack!"}


@app.get("/health")
def health():
    return {"status": "ok"}