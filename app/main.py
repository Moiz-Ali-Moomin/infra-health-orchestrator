from fastapi import FastAPI
from app.api.routes import router
from app.utils.logger import setup_logger
from app.config import settings

logger = setup_logger(__name__)

app = FastAPI(
    title="System Health Validator",
    description="Production-grade API for validating system and Kubernetes environment health.",
    version="1.0.0",
)

app.include_router(router)

@app.on_event("startup")
async def startup_event():
    logger.info(f"System Health Validator starting up on port {settings.API_PORT}...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=settings.API_PORT, 
        log_level=settings.LOG_LEVEL.lower()
    )
