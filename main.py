from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from Controllers.monitoring_controller import router as monitoring_router
from Security.config import (
    ALLOWED_HOSTS,
    CORS_ORIGINS,
    DOCS_ENABLED,
    HTTPS_ONLY,
    MAX_REQUEST_BODY_BYTES,
)
from Security.middleware import RequestBodyLimitMiddleware, SecurityHeadersMiddleware
from infra.influxdb_repository import close


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        close()


app = FastAPI(
    title="Sentinela API",
    description="API de monitoramento preditivo de infraestrutura.",
    version="0.1.0",
    docs_url="/docs" if DOCS_ENABLED else None,
    redoc_url="/redoc" if DOCS_ENABLED else None,
    openapi_url="/openapi.json" if DOCS_ENABLED else None,
    lifespan=lifespan,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS, www_redirect=False)

if HTTPS_ONLY:
    app.add_middleware(HTTPSRedirectMiddleware)

if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "X-Sentinela-Ingest-Key",
            "X-Sentinela-Read-Key",
        ],
    )

app.add_middleware(
    RequestBodyLimitMiddleware,
    max_body_bytes=MAX_REQUEST_BODY_BYTES,
)
app.add_middleware(SecurityHeadersMiddleware, include_hsts=HTTPS_ONLY)

app.include_router(monitoring_router)
