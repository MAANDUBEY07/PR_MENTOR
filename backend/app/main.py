from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import cors_origins
from app.database.connection import connection
from app.routes.auth import router as auth_router
from app.routes.learning import router as learning_router
from app.routes.review import router as review_router

app = FastAPI(title="PR Mentor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "pr-mentor"}


@app.get("/api/health")
def api_health():
    return health()


@app.get("/api/health/ready")
def readiness():
    with connection():
        pass
    return {"status": "ready", "service": "pr-mentor"}


app.include_router(review_router)
app.include_router(learning_router)
app.include_router(auth_router)
