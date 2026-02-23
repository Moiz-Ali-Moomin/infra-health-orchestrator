from fastapi import APIRouter, HTTPException, status
from app.services.health_orchestrator import HealthOrchestrator
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()
orchestrator = HealthOrchestrator()

@router.get("/health/live", summary="Liveness Probe")
async def liveness_check():
    """Basic check to confirm the API is running."""
    return {"status": "alive"}

@router.get("/health/ready", summary="Readiness Probe")
async def readiness_check():
    """
    Fast aggregated check for Kubernetes readiness probe.
    (Note: Typically lighter than a full system validation; 
    can be expanded to check specific critical dependencies).
    """
    return {"status": "ready"}

@router.post("/health/run", summary="Run Full System Validation")
async def run_validation():
    """
    Executes a full suite of system health validations:
    - HTTP endpoints
    - Kubernetes resources
    - Database connectivity
    - System resources
    
    Returns 503 Service Unavailable if any critical check fails.
    """
    logger.info("Received request to run full system validation.")
    
    results = orchestrator.run_all()
    
    if results["status"] != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=results
        )
        
    return results
