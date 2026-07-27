import os

from dotenv import load_dotenv

load_dotenv()


def _csv_setting(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def _bool_setting(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a valid boolean value.")


def _positive_int_setting(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return value


ALLOWED_HOSTS = _csv_setting(
    "SENTINELA_ALLOWED_HOSTS",
    "127.0.0.1,localhost,testserver",
)
CORS_ORIGINS = _csv_setting("SENTINELA_CORS_ORIGINS")
ALLOWED_MEASUREMENTS = frozenset(
    _csv_setting("SENTINELA_ALLOWED_MEASUREMENTS", "system_metrics")
)
ALLOWED_TAG_KEYS = frozenset(
    _csv_setting(
        "SENTINELA_ALLOWED_TAG_KEYS",
        "host_id,machine_type,environment,os",
    )
)

DOCS_ENABLED = _bool_setting("SENTINELA_DOCS_ENABLED", default=True)
HTTPS_ONLY = _bool_setting("SENTINELA_HTTPS_ONLY", default=False)
MAX_REQUEST_BODY_BYTES = _positive_int_setting(
    "SENTINELA_MAX_REQUEST_BODY_BYTES",
    32 * 1024,
)

RATE_LIMIT_STORAGE_URI = os.getenv(
    "SENTINELA_RATE_LIMIT_STORAGE_URI",
    "memory://",
)
INGEST_RATE_LIMIT = os.getenv("SENTINELA_INGEST_RATE_LIMIT", "30/minute")
READ_RATE_LIMIT = os.getenv("SENTINELA_READ_RATE_LIMIT", "60/minute")
HEALTH_RATE_LIMIT = os.getenv("SENTINELA_HEALTH_RATE_LIMIT", "120/minute")
