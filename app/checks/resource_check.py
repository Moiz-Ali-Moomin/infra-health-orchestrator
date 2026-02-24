import time
import psutil
import asyncio
from app.utils.logger import setup_logger
from app.config import settings
from app.checks.base import BaseCheck
from app.engine.models import CheckResultDTO, CheckStatus, Severity

logger = setup_logger(__name__)

class ResourceCheck(BaseCheck):
    """Validates system resource usage (CPU and Memory)."""
    
    @property
    def name(self) -> str:
        return "resource_check"

    async def run(self, **kwargs) -> CheckResultDTO:
        logger.info("Running Resource health check...")
        start_time = time.time()
        
        try:
            # We wrap in thread block to perform psutil blocking calls gracefully
            def _get_resources():
                cpu = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory().percent
                return cpu, mem
                
            cpu_percent, mem_percent = await asyncio.to_thread(_get_resources)
            
            logger.debug(f"CPU Usage: {cpu_percent}%, Memory Usage: {mem_percent}%")
            
            details = {
                "cpu_usage_percent": cpu_percent,
                "mem_usage_percent": mem_percent,
                "cpu_threshold": settings.CPU_THRESHOLD_PERCENT,
                "mem_threshold": settings.MEM_THRESHOLD_PERCENT
            }
            
            if cpu_percent > settings.CPU_THRESHOLD_PERCENT:
                logger.error(f"CPU usage ({cpu_percent}%) exceeds threshold")
                return self.build_result(
                    status=CheckStatus.UNHEALTHY,
                    latency_sec=round(time.time() - start_time, 3),
                    details=details,
                    severity=Severity.CRITICAL,
                    error_message=f"CPU exceeds {settings.CPU_THRESHOLD_PERCENT}%"
                )
                
            if mem_percent > settings.MEM_THRESHOLD_PERCENT:
                logger.error(f"Memory usage ({mem_percent}%) exceeds threshold")
                return self.build_result(
                    status=CheckStatus.UNHEALTHY,
                    latency_sec=round(time.time() - start_time, 3),
                    details=details,
                    severity=Severity.CRITICAL,
                    error_message=f"MEM exceeds {settings.MEM_THRESHOLD_PERCENT}%"
                )
                
            logger.info("Resource health check passed.")
            return self.build_result(
                status=CheckStatus.HEALTHY,
                latency_sec=round(time.time() - start_time, 3),
                details=details,
                severity=Severity.INFO
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch system resources: {e}")
            return self.build_result(
                status=CheckStatus.UNHEALTHY,
                latency_sec=round(time.time() - start_time, 3),
                details={"info": f"Error fetching resources: {str(e)}"},
                severity=Severity.CRITICAL,
                error_message=str(e)
            )
