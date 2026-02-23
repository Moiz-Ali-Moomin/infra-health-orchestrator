import time
from datetime import datetime, timezone
from app.utils.logger import setup_logger
from app.checks.http_check import HTTPCheck
from app.checks.kubernetes_check import KubernetesCheck
from app.checks.database_check import DatabaseCheck
from app.checks.resource_check import ResourceCheck
from app.services.notifier import Notifier

logger = setup_logger(__name__)

class HealthOrchestrator:
    """Orchestrates all system health checks and compiles the final result."""
    
    def __init__(self):
        self.checks = {
            "http": HTTPCheck,
            "kubernetes": KubernetesCheck,
            "database": DatabaseCheck,
            "resources": ResourceCheck
        }

    def run_all(self) -> dict:
        logger.info("Starting orchestrated system health validation.")
        
        results = {}
        all_healthy = True
        total_latency = 0.0
        start_time_total = time.time()
        
        for name, check_class in self.checks.items():
            try:
                check_result = check_class.run()
                
                # Check status
                if check_result.get("status") != "healthy":
                    all_healthy = False
                    Notifier.alert_failure(name, check_result.get("details", {}))
                    
                total_latency += check_result.get("latency_sec", 0.0)
                results[name] = check_result
                
            except Exception as e:
                logger.exception(f"Unhandled exception running check '{name}': {e}")
                all_healthy = False
                error_details = {"error": str(e)}
                Notifier.alert_failure(name, error_details)
                
                results[name] = {
                    "status": "unhealthy",
                    "details": error_details,
                    "latency_sec": 0.0
                }

        total_latency = round(time.time() - start_time_total, 3)
        final_status = "healthy" if all_healthy else "unhealthy"
        
        if final_status == "healthy":
            logger.info(f"All orchestrated checks passed in {total_latency}s. System is HEALTHY.")
        else:
            logger.error(f"Orchestrated checks failed in {total_latency}s. System is UNHEALTHY.")
            
        return {
            "status": final_status,
            "details": results,
            "latency_sec": total_latency,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
