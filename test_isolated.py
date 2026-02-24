import asyncio
from app.engine.models import CheckResultDTO, CheckStatus, Severity
from app.engine.correlation_engine import CorrelationEngine
from app.engine.policy_engine import PolicyEngine
from app.engine.slo_engine import SLOEngine

async def test_governance():
    print("=== Isolated Governance Math Test ===")
    
    # 1. Mock Check Results (e.g. Database failed, HTTP degraded)
    mock_results = [
        CheckResultDTO(check_type="database_check", status=CheckStatus.UNHEALTHY, latency_sec=5.1, severity=Severity.CRITICAL),
        CheckResultDTO(check_type="http_check", status=CheckStatus.DEGRADED, latency_sec=2.4, severity=Severity.WARNING),
        CheckResultDTO(check_type="kubernetes_check", status=CheckStatus.HEALTHY, latency_sec=0.1, severity=Severity.INFO)
    ]
    
    # 2. Correlate Failures
    corr = CorrelationEngine()
    ctx = corr.correlate_failures(mock_results)
    
    print(f"Root Cause: {ctx.root_cause_identified}")  # Should be database_check
    print(f"Impacted Sptms: {ctx.impacted_dependencies}") # Should include http_check
    
    # 3. Policy Execution
    # We pass an empty slo_engine dict to mock standard passing
    pol_engine = PolicyEngine("policies/prod.yaml") # Even if missing, falls back
    decision = pol_engine.evaluate_policy("production", mock_results, {})
    
    print(f"Decision: {decision.action.value}")      # Should be BLOCK due to CRITICAL DB
    print(f"Reason: {decision.reason}")
    

if __name__ == "__main__":
    asyncio.run(test_governance())
