import time
import psycopg
import asyncio
from app.utils.logger import setup_logger
from app.config import settings
from app.checks.base import BaseCheck
from app.engine.models import CheckResultDTO, CheckStatus, Severity

logger = setup_logger(__name__)

class DatabaseCheck(BaseCheck):
    """Validates PostgreSQL Database Connectivity and latency."""
    
    @property
    def name(self) -> str:
        return "database_check"

    async def run(self, **kwargs) -> CheckResultDTO:
        logger.info("Running Database health check...")
        start_time = time.time()
        
        try:
            # We use thread for psycopg to avoid blocking, asyncpg could be used for advanced async
            def _connect_and_query():
                conn = psycopg.connect(
                    host=settings.DB_HOST,
                    port=settings.DB_PORT,
                    user=settings.DB_USER,
                    password=settings.DB_PASSWORD,
                    dbname=settings.DB_NAME,
                    connect_timeout=settings.DB_TIMEOUT_SEC
                )
                cursor = conn.cursor()
                cursor.execute("SELECT 1;")
                res = cursor.fetchone()
                cursor.close()
                conn.close()
                return res

            result = await asyncio.to_thread(_connect_and_query)
            latency = time.time() - start_time
            
            if result and result[0] == 1:
                if latency > settings.DB_TIMEOUT_SEC:
                    logger.error(f"Database query latency high: {latency:.2f}s")
                    return self.build_result(
                        status=CheckStatus.UNHEALTHY,
                        latency_sec=round(latency, 3),
                        details={"info": f"Latency too high: {latency:.2f}s"},
                        severity=Severity.CRITICAL,
                        error_message="High latency"
                    )
                    
                logger.info("Database health check passed.")
                return self.build_result(
                    status=CheckStatus.HEALTHY,
                    latency_sec=round(latency, 3),
                    details={"info": "Connected and executed SELECT 1"},
                    severity=Severity.INFO
                )
            else:
                logger.error("Database query returned unexpected result.")
                return self.build_result(
                    status=CheckStatus.UNHEALTHY,
                    latency_sec=round(latency, 3),
                    details={"info": "Unexpected query result"},
                    severity=Severity.CRITICAL,
                    error_message="Unexpected result"
                )
                
        except psycopg.OperationalError as e:
            logger.error(f"Database connection failed: {e}")
            latency = time.time() - start_time
            return self.build_result(
                status=CheckStatus.UNHEALTHY,
                latency_sec=round(latency, 3),
                details={"info": f"Connection Error: {str(e)}"},
                severity=Severity.CRITICAL,
                error_message=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error during Database check: {e}")
            latency = time.time() - start_time
            return self.build_result(
                status=CheckStatus.UNHEALTHY,
                latency_sec=round(latency, 3),
                details={"info": f"Unexpected Error: {str(e)}"},
                severity=Severity.CRITICAL,
                error_message=str(e)
            )
