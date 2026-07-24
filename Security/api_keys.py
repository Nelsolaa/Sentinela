import logging
import os
import secrets
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

MINIMUM_API_KEY_LENGTH = 32

ingest_key_header = APIKeyHeader(
    name="X-Sentinela-Ingest-Key",
    scheme_name="SentinelaIngestKey",
    auto_error=False,
)
read_key_header = APIKeyHeader(
    name="X-Sentinela-Read-Key",
    scheme_name="SentinelaReadKey",
    auto_error=False,
)


def _configured_key(name: str) -> str:
    value = os.getenv(name, "").strip()
    lowered = value.lower()

    if (
        len(value) < MINIMUM_API_KEY_LENGTH
        or "change-me" in lowered
        or "replace" in lowered
    ):
        logger.error("Required service key %s is not securely configured.", name)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API security is not configured.",
        )

    return value


def _verify_key(name: str, provided: str | None) -> None:
    expected = _configured_key(name)

    if provided is None or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing service key.",
        )


def verify_ingest_api_key(
    api_key: Annotated[str | None, Security(ingest_key_header)],
) -> None:
    _verify_key("SENTINELA_INGEST_API_KEY", api_key)


def verify_read_api_key(
    api_key: Annotated[str | None, Security(read_key_header)],
) -> None:
    _verify_key("SENTINELA_READ_API_KEY", api_key)
