import time
import psutil
from app.utils.logger import setup_logger
from app.config import settings

logger = setup_logger(__name__)

class ResourceCheck:
    """Validates system resource usage (CPU and Memory)."""
    
    @staticmethod
    def run() -> dict:
        logger.info("Running Resource health check...")
        start_time = time.time()
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            mem_info = psutil.virtual_memory()
            mem_percent = mem_info.percent
            
            logger.debug(f"CPU Usage: {cpu_percent}%, Memory Usage: {mem_percent}%")
            
            details = {
                "cpu_usage_percent": cpu_percent,
                "mem_usage_percent": mem_percent,
                "cpu_threshold": settings.CPU_THRESHOLD_PERCENT,
                "mem_threshold": settings.MEM_THRESHOLD_PERCENT
            }
            
            if cpu_percent > settings.CPU_THRESHOLD_PERCENT:
                logger.error(f"CPU usage ({cpu_percent}%) exceeds threshold")
                return {
                    "status": "unhealthy",
                    "details": details,
                    "latency_sec": round(time.time() - start_time, 3)
                }
                
            if mem_percent > settings.MEM_THRESHOLD_PERCENT:
                logger.error(f"Memory usage ({mem_percent}%) exceeds threshold")
                return {
                    "status": "unhealthy",
                    "details": details,
                    "latency_sec": round(time.time() - start_time, 3)
                }
                
            logger.info("Resource health check passed.")
            return {
                "status": "healthy",
                "details": details,
                "latency_sec": round(time.time() - start_time, 3)
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch system resources: {e}")
            return {
                "status": "unhealthy",
                "details": f"Error fetching resources: {str(e)}",
                "latency_sec": round(time.time() - start_time, 3)
            }
