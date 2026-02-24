import time
import asyncio
from typing import Dict, List
from app.engine.plugin_loader import PluginLoader
from app.engine.models import CheckResultDTO, CheckStatus, Severity
from app.utils.circuit_breaker import CircuitBreakerFactory, CircuitBreaker
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class Orchestrator:
    """Bounded, concurrent execution engine for validation plugins."""

    def __init__(
        self, 
        plugin_loader: PluginLoader,
        circuit_breaker_factory: CircuitBreakerFactory,
        max_concurrent: int,
        global_timeout: float
    ):
        self.plugins = plugin_loader.load_checks()
        self.breakers: Dict[str, CircuitBreaker] = {
            name: circuit_breaker_factory.get_breaker(name) for name in self.plugins.keys()
        }
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.global_timeout = global_timeout

    async def execute_all(self, cluster_name: str = "local") -> List[CheckResultDTO]:
        logger.info(f"Orchestrating {len(self.plugins)} checks...")
        start_time = time.time()
        
        tasks = []
        for name, plugin in self.plugins.items():
            tasks.append(self._execute_check(name, plugin, cluster_name))
            
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.global_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Global execution timeout exceeded ({self.global_timeout}s)")
            results = []
            
        valid_results = []
        for res in results:
            if isinstance(res, CheckResultDTO):
                valid_results.append(res)
            elif isinstance(res, Exception):
                logger.error(f"Uncaught exception during execution: {res}")
                
        logger.info(f"Orchestration completed in {time.time() - start_time:.3f}s")
        return valid_results

    async def _execute_check(self, name: str, plugin, cluster_name: str) -> CheckResultDTO:
        breaker = self.breakers.get(name)
        
        if breaker and not await breaker.can_execute():
            logger.warning(f"Circuit Breaker OPEN for {name}. Fast-failing.")
            return plugin.build_result(
                status=CheckStatus.UNHEALTHY,
                latency_sec=0.0,
                severity=Severity.CRITICAL,
                cluster=cluster_name,
                error_message="Circuit Breaker OPEN",
                details={"info": "Check aborted by distributed CircuitBreaker"}
            )

        async with self.semaphore:
            try:
                # 10s individual timeout
                result = await asyncio.wait_for(
                    plugin.run(cluster_name=cluster_name),
                    timeout=10.0
                )
                
                if result.status == CheckStatus.UNHEALTHY and breaker:
                    await breaker.record_failure()
                elif result.status == CheckStatus.HEALTHY and breaker:
                    await breaker.record_success()
                    
                return result
            except asyncio.TimeoutError:
                logger.error(f"Plugin {name} timed out.")
                if breaker:
                    await breaker.record_failure()
                return plugin.build_result(
                    status=CheckStatus.UNHEALTHY,
                    latency_sec=10.0,
                    severity=Severity.CRITICAL,
                    cluster=cluster_name,
                    error_message="Check execution timeout"
                )
            except Exception as e:
                logger.error(f"Plugin {name} failed catastrophically: {e}")
                if breaker:
                    await breaker.record_failure()
                return plugin.build_result(
                    status=CheckStatus.UNHEALTHY,
                    latency_sec=0.0,
                    severity=Severity.CRITICAL,
                    cluster=cluster_name,
                    error_message=f"Catastrophic plugin failure: {str(e)}"
                )
