from typing import Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from app.repositories.interfaces import ValidationRepositoryInterface
from app.engine.models import ValidationRunDTO, PolicyAction
from app.infrastructure.database.models import DBValidationRun, DBCheckResult

class SQLValidationRepository(ValidationRepositoryInterface):
    """Concrete implementation of Validation Repository mapping to PostgreSQL via SQLAlchemy Async."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def save_run(self, run_data: ValidationRunDTO) -> None:
        db_run = DBValidationRun(
            run_id=run_data.run_id,
            correlation_id=run_data.correlation_id,
            environment=run_data.environment,
            caller_identity=run_data.caller_identity,
            caller_role=run_data.caller_role,
            caller_ip=run_data.caller_ip,
            trigger_source=run_data.trigger_source,
            status=run_data.status,
            policy_decision=run_data.policy_decision.action.value,
            policy_reason=run_data.policy_decision.reason,
            total_latency_sec=run_data.latency_sec,
            timestamp=run_data.timestamp,
            correlation_root_cause=run_data.correlation_summary.root_cause_identified
        )

        checks = []
        for _, check in run_data.details.items():
            db_check = DBCheckResult(
                check_type=check.check_type,
                cluster=check.cluster,
                status=check.status.value,
                latency_sec=check.latency_sec,
                severity=check.severity.value,
                error_message=check.error_message,
                details=check.details,
                timestamp=run_data.timestamp
            )
            checks.append(db_check)
            
        db_run.checks = checks

        try:
            async with self.session_factory() as session:
                session.add(db_run)
                await session.commit()
        except Exception as e:
            # Graceful Degradation: If DB writes fail, fallback to local WAL
            from app.utils.logger import setup_logger
            logger = setup_logger(__name__)
            logger.error(f"PostgreSQL persistence failed: {e}. Writing to fallback WAL.")
            # Emit Metric: validation_persistence_failure_total (handled via Prometheus wrapper eventually)
            with open("fallback_runs.wal", "a") as f:
                f.write(run_data.model_dump_json() + "\n")

    async def get_historical_stats(self, service_id: str, time_window_days: int) -> Dict[str, Any]:
        """Calculates mock availability / burn rate stats.
        In a real application this would query the specific service checks."""
        # For demonstration purposes, returning mock stats representing real SQL grouping
        return {
            "availability_percent": 99.85,
            "burn_rate": 0.5
        }
