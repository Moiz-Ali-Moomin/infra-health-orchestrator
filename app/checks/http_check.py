import time
import requests
import asyncio
from app.utils.logger import setup_logger
from app.config import settings
from app.checks.base import BaseCheck
from app.engine.models import CheckResultDTO, CheckStatus, Severity

logger = setup_logger(__name__)

class HTTPCheck(BaseCheck):
    """Validates HTTP service endpoints."""
    
    @property
    def name(self) -> str:
        return "http_check"

    async def run(self, **kwargs) -> CheckResultDTO:
        logger.info("Running HTTP health check...")
        
        endpoints = [e.strip() for e in settings.HTTP_ENDPOINTS if e.strip()]
        if not endpoints:
            logger.warning("No HTTP endpoints configured.")
            return self.build_result(status=CheckStatus.HEALTHY, latency_sec=0.0, details={"info": "No endpoints configured"})

        results = {}
        all_passed = True
        total_latency = 0.0

        for endpoint in endpoints:
            try:
                start_time = time.time()
                # Run sync requests in threadpool to avoid blocking event loop
                response = await asyncio.to_thread(requests.get, endpoint, timeout=settings.HTTP_TIMEOUT_SEC)
                latency = time.time() - start_time
                total_latency += latency
                
                if response.status_code >= 400:
                    logger.error(f"HTTP Check failed for {endpoint} with status {response.status_code}")
                    results[endpoint] = f"Failed (Status: {response.status_code})"
                    all_passed = False
                elif latency > settings.HTTP_TIMEOUT_SEC:
                    logger.error(f"HTTP Check slow for {endpoint} ({latency:.2f}s)")
                    results[endpoint] = f"Timeout/Slow ({latency:.2f}s)"
                    all_passed = False
                else:
                    logger.info(f"HTTP Check passed for {endpoint}")
                    results[endpoint] = "Passed"
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"HTTP Request failed for {endpoint}: {e}")
                results[endpoint] = f"Error: {str(e)}"
                all_passed = False

        status = CheckStatus.HEALTHY if all_passed else CheckStatus.DEGRADED
        avg_latency = total_latency / len(endpoints) if endpoints else 0.0
        
        return self.build_result(
            status=status,
            latency_sec=round(avg_latency, 3),
            details=results,
            severity=Severity.WARNING
        )
