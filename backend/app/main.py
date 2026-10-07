"""GroupWise AI — API service.

Layers: auth → data (SQLAlchemy) → deterministic finance (app.core) → analytics (app.analytics)
→ ML (app.ml) → recommendations (app.analytics.insights) → LLM explanation (app.llm, app.copilot).
"""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .api import auth, expenses, groups, intelligence, meta, notifications, wallet
from .config import get_settings
from .db import init_db
from .services.audit import AuditMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("groupwise")


def _warm_models() -> None:
    from .copilot.intents import _get_model
    from .ml.categorizer import get_categorizer

    get_categorizer()
    _get_model()
    log.info("ML models ready")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    threading.Thread(target=_warm_models, daemon=True).start()
    yield


settings = get_settings()
app = FastAPI(title="GroupWise AI API", version="1.0.0", lifespan=lifespan,
              description="Shared financial intelligence: deterministic finance + ML + grounded LLM explanations.",
              docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(AuditMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["Authorization", "Content-Type"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else response.headers.get(
        "Cache-Control", "no-store")
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):  # never leak internals to the client
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again."})


for r in (meta.router, auth.router, groups.router, expenses.router, intelligence.router, notifications.router,
          wallet.router):
    app.include_router(r, prefix="/api")


@app.get("/")
def root() -> dict:
    return {"service": "GroupWise AI API", "docs": "/api/docs", "health": "/api/health"}
