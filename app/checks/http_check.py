import time
import requests
from app.utils.logger import setup_logger
from app.config import settings

logger = setup_logger(__name__)

class HTTPCheck:
    """Validates HTTP service endpoints."""
    
    @staticmethod
    def run() -> dict:
        logger.info("Running HTTP health check...")
        
        endpoints = [e.strip() for e in settings.HTTP_ENDPOINTS if e.strip()]
        if not endpoints:
            logger.warning("No HTTP endpoints configured.")
            return {"status": "healthy", "details": "No endpoints configured", "latency_sec": 0.0}

        results = {}
        all_passed = True
        total_latency = 0.0

        for endpoint in endpoints:
            try:
                start_time = time.time()
                response = requests.get(endpoint, timeout=settings.HTTP_TIMEOUT_SEC)
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

        status = "healthy" if all_passed else "unhealthy"
        avg_latency = total_latency / len(endpoints) if endpoints else 0.0
        
        return {
            "status": status,
            "details": results,
            "latency_sec": round(avg_latency, 3)
        }
