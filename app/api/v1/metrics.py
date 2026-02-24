from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

router = APIRouter(tags=["Metrics"])

@router.get("/metrics")
def get_metrics():
    """Exposes Prometheus scraper endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
