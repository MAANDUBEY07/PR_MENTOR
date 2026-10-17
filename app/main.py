"""FastAPI application for PR Mentor."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes.auth import router as auth_router
from app.routes.review import router as review_router
from app.routes.learning import router as learning_router
from app.database.connection import connect, close, is_ready
from app.config import settings

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("pr_mentor")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("MONGODB_URI"):
        try:
            connect()
        except Exception as exc:
            logger.error("MongoDB connection unavailable at startup: %s", type(exc).__name__)
    yield
    close()


app = FastAPI(title=settings.app_name, version="1.0.0", debug=settings.debug, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.frontend_origins), allow_credentials=False, allow_methods=["GET", "POST", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])
app.include_router(auth_router)
app.include_router(review_router)
app.include_router(learning_router)


@app.get("/")
def root():
    return {"service": "PR Mentor API", "docs": "/docs"}


@app.get("/api/health")
@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name, "version": app.version, "mode": "demo" if settings.demo_mode else "live"}


@app.get("/api/health/ready")
def readiness():
    configured = bool(os.getenv("MONGODB_URI"))
    mongodb_ready = is_ready()
    response = {"status": "ok" if mongodb_ready else "unavailable", "dependencies": {"mongodb": "ready" if mongodb_ready and configured else "optional_unconfigured" if not configured else "unavailable", "github": "configured" if os.getenv("GITHUB_TOKEN") else "public_api"}}
    return JSONResponse(status_code=200 if mongodb_ready else 503, content=response)
