import time
import psycopg
from app.utils.logger import setup_logger
from app.config import settings

logger = setup_logger(__name__)

class DatabaseCheck:
    """Validates PostgreSQL Database Connectivity and latency."""
    
    @staticmethod
    def run() -> dict:
        logger.info("Running Database health check...")
        start_time = time.time()
        
        try:
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
            result = cursor.fetchone()
            
            latency = time.time() - start_time
            cursor.close()
            conn.close()
            
            if result and result[0] == 1:
                if latency > settings.DB_TIMEOUT_SEC:
                    logger.error(f"Database query latency high: {latency:.2f}s")
                    return {
                        "status": "unhealthy", 
                        "details": f"Latency too high: {latency:.2f}s", 
                        "latency_sec": round(latency, 3)
                    }
                    
                logger.info("Database health check passed.")
                return {
                    "status": "healthy",
                    "details": "Connected and executed SELECT 1",
                    "latency_sec": round(latency, 3)
                }
            else:
                logger.error("Database query returned unexpected result.")
                return {
                    "status": "unhealthy",
                    "details": "Unexpected query result",
                    "latency_sec": round(latency, 3)
                }
                
        except psycopg.OperationalError as e:
            logger.error(f"Database connection failed: {e}")
            latency = time.time() - start_time
            return {
                "status": "unhealthy",
                "details": f"Connection Error: {str(e)}",
                "latency_sec": round(latency, 3)
            }
        except Exception as e:
            logger.error(f"Unexpected error during Database check: {e}")
            latency = time.time() - start_time
            return {
                "status": "unhealthy", 
                "details": f"Unexpected Error: {str(e)}", 
                "latency_sec": round(latency, 3)
            }
