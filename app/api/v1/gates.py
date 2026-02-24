import uuid
from datetime import datetime, timezone
import asyncio
from fastapi import APIRouter, BackgroundTasks, Header, Depends, Request
from dependency_injector.wiring import inject, Provide

from app.engine.orchestrator import Orchestrator
from app.engine.policy_engine import PolicyEngine
from app.engine.slo_engine import SLOEngine
from app.engine.correlation_engine import CorrelationEngine
from app.repositories.interfaces import ValidationRepositoryInterface
from app.engine.models import ValidationRunDTO, PolicyDecisionDTO, PolicyAction
from app.containers import Container
from app.config import settings
from app.utils.logger import correlation_id_ctx, principal_id_ctx

# In metrics Layer
from app.infrastructure.observability.metrics import VALIDATOR_RUNS_TOTAL, CHECK_STATUS_TOTAL, CHECK_LATENCY_SECONDS, SLO_BURN_RATE

router = APIRouter(prefix="/v1/gates", tags=["Deployment Gates"])

@router.post("/deploy", response_model=ValidationRunDTO)
@inject
async def evaluate_deployment_gate(
    request: Request,
    background_tasks: BackgroundTasks,
    x_correlation_id: str = Header(default_factory=lambda: str(uuid.uuid4())),
    orchestrator: Orchestrator = Depends(Provide[Container.orchestrator]),
    policy_engine: PolicyEngine = Depends(Provide[Container.policy_engine]),
    slo_engine: SLOEngine = Depends(Provide[Container.slo_engine]),
    correlation_engine: CorrelationEngine = Depends(Provide[Container.correlation_engine]),
    repo: ValidationRepositoryInterface = Depends(Provide[Container.validation_repo])
):
    """Executes a full validation suite as a CI/CD gated check securely."""
    
    # 0. Context Injection for Observability
    token_corr = correlation_id_ctx.set(x_correlation_id)
    
    # Identity mapped via AuthMiddleware
    caller_identity = getattr(request.state, "caller_identity", "anonymous")
    caller_role = getattr(request.state, "caller_role", "guest")
    caller_ip = request.client.host if request.client else "unknown"
    
    # 1. Execute all checks
    check_results = await orchestrator.execute_all(cluster_name="local")
    
    for r in check_results:
        # Export prometheus metrics
        CHECK_STATUS_TOTAL.labels(
            environment=settings.ENVIRONMENT,
            check_type=r.check_type,
            cluster=r.cluster,
            status=r.status.value
        ).inc()
        CHECK_LATENCY_SECONDS.labels(
            check_type=r.check_type,
            cluster=r.cluster
        ).observe(r.latency_sec)
        
    # 2. Correlate Failures
    correlation_ctx = correlation_engine.correlate_failures(check_results)
    
    # 3. Evaluate SLOs
    slo_states = await slo_engine.evaluate_all()
    for svc, state in slo_states.items():
        SLO_BURN_RATE.labels(service_id=svc, window="7d").set(state.burn_rate)
    
    # 4. Evaluate Policy
    decision = policy_engine.evaluate_policy(
        environment=settings.ENVIRONMENT,
        check_results=check_results,
        slo_state=slo_states
    )
    
    total_latency = sum([r.latency_sec for r in check_results])
    
    # 5. Build Final DTO
    run_dto = ValidationRunDTO(
        run_id=str(uuid.uuid4()),
        correlation_id=x_correlation_id,
        environment=settings.ENVIRONMENT,
        caller_identity=caller_identity,
        caller_role=caller_role,
        caller_ip=caller_ip,
        trigger_source="deploy-hook",
        status="degraded" if decision.action != PolicyAction.ALLOW else "healthy",
        policy_decision=decision,
        correlation_summary=correlation_ctx,
        slo_state=slo_states,
        details={r.check_type: r for r in check_results},
        latency_sec=round(total_latency, 3),
        timestamp=datetime.now(timezone.utc)
    )
    
    # Record top-level metric
    VALIDATOR_RUNS_TOTAL.labels(
        environment=settings.ENVIRONMENT,
        trigger="deploy-hook",
        decision=decision.action.value
    ).inc()

    # 6. Fire-and-forget save to PostgreSQL
    background_tasks.add_task(repo.save_run, run_dto)
    
    # Cleanup context
    correlation_id_ctx.reset(token_corr)
    
    return run_dto
