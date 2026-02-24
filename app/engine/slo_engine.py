import yaml
from typing import Dict
from app.engine.models import SLOStateDTO
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class SLOEngine:
    """Calculates Error budgets and Availability based on historical validation telemetry."""

    def __init__(self, slos_path: str, validation_repo):
        self.slos_path = slos_path
        self.repo = validation_repo
        self.slos = self._load_slos()

    def _load_slos(self) -> Dict:
        try:
            with open(self.slos_path, 'r') as f:
                data = yaml.safe_load(f)
                return {slo['service_id']: slo for slo in data.get('slos', [])}
        except Exception as e:
            logger.warning(f"Could not load SLO definitions: {e}")
            return {}

    async def evaluate_slo(self, service_id: str) -> SLOStateDTO:
        slo_def = self.slos.get(service_id)
        if not slo_def:
            # Dummy state if not defined
            return SLOStateDTO(
                availability_7d=100.0,
                target=99.9,
                burn_rate=0.0,
                decision="healthy"
            )
            
        window_days = slo_def.get("rolling_window_days", 7)
        target = slo_def.get("target_availability_percent", 99.9)
        burn_alert = slo_def.get("thresholds", {}).get("burn_rate_alert", 2.0)
        
        try:
            # Calculate from repository history mapping service to past checks
            stats = await self.repo.get_historical_stats(service_id, window_days)
            avail = stats["availability_percent"]
            burn_rate = stats["burn_rate"]
        except Exception as e:
            # Graceful Degradation: If the database is down, we cannot evaluate SLOs.
            # We fail-open by returning an 'unknown' state that the PolicyEngine will ALLOW.
            logger.error(f"Degraded SLO evaluation for {service_id} due to persistence failure: {e}")
            # Emit Metric: slo_evaluation_fallback_total
            return SLOStateDTO(
                availability_7d=0.0,
                target=target,
                burn_rate=0.0,
                decision="unknown"
            )
        
        decision = "healthy"
        if burn_rate >= burn_alert:
            decision = "burning"
        if avail < target:
            decision = "budget_exhausted"
            
        return SLOStateDTO(
            availability_7d=round(avail, 2),
            target=target,
            burn_rate=round(burn_rate, 2),
            decision=decision
        )

    async def evaluate_all(self) -> Dict[str, SLOStateDTO]:
        states = {}
        for service_id in self.slos.keys():
            states[service_id] = await self.evaluate_slo(service_id)
        return states
