from fastapi import APIRouter
from app.api.v1.gates import router as gates_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.audit import router as audit_router

router = APIRouter()

# Standard Minimal K8s Probes
@router.get("/health/live", summary="Liveness Probe", tags=["Probes"])
async def liveness_check():
    """Minimal assertion that the ASGI server loop is running."""
    return {"status": "alive"}

@router.get("/health/ready", summary="Readiness Probe", tags=["Probes"])
async def readiness_check():
    """Assertion that the execution engine is ready to receive checks."""
    return {"status": "ready"}

# Mount Advanced V1 Reliability & Governance Sub-Routers
router.include_router(gates_router)
router.include_router(metrics_router)
router.include_router(audit_router)
