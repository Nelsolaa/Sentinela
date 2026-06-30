from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from Controllers.metrics_controller import router as metrics_router

app = FastAPI(
    title="Sentinela API",
    description="API de monitoramento preditivo de infraestrutura.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
