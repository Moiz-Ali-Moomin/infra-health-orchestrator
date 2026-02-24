import asyncio
from fastapi import FastAPI
from app.api.routes import router
from app.utils.logger import setup_logger
from app.config import settings
from app.infrastructure.database.session import init_db
from app.containers import Container
from app.api.middleware.auth import AuthMiddleware
from app.api.middleware.idempotency import IdempotencyMiddleware

logger = setup_logger(__name__)

def create_app() -> FastAPI:
    container = Container()
    
    app = FastAPI(
        title="System Health Validator [Evolution]",
        description="Time-aware SLO-driven Reliability Governance Engine.",
        version="2.1.0",
    )
    
    app.container = container
    
    # Middleware Evaluation Order: 
    # 1. Auth (Extract Identity)
    # 2. Idempotency (Lock via Identity + Header)
    app.add_middleware(
        IdempotencyMiddleware,
        redis_client=container.redis_pool()
    )
    app.add_middleware(AuthMiddleware)

    app.include_router(router)
    return app

app = create_app()

@app.on_event("startup")
async def startup_event():
    # logger.info("Initializing Tracing (OpenTelemetry)...")
    # init_tracing()
    # FastAPIInstrumentor.instrument_app(app)
    
    logger.info("Initializing Postgres Database schemas...")
    await init_db()
    
    logger.info(f"Reliability Governance Engine starting on port {settings.API_PORT}...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=settings.API_PORT, 
        log_level=settings.LOG_LEVEL.lower()
    )
