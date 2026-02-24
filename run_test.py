import asyncio
import json
from datetime import datetime
from app.engine.orchestrator import Orchestrator
from app.engine.correlation_engine import CorrelationEngine
from app.engine.policy_engine import PolicyEngine
from app.engine.slo_engine import SLOEngine
from app.repositories.validation_repo import SQLValidationRepository
from app.infrastructure.database.session import AsyncSessionFactory, init_db
from app.config import settings

async def main():
    print("=== System Health Validator Migration Test ===")
    print("1. Initializing DB schemas...")
    await init_db()
    
    print("2. Booting Orchestrator...")
    orchestrator = Orchestrator()
    repo = SQLValidationRepository(AsyncSessionFactory)
    slo_engine = SLOEngine(settings.SLO_PATH, repo)
    policy_engine = PolicyEngine(settings.POLICY_PATH)
    correlation_engine = CorrelationEngine()

    print("3. Executing Validation Checks...")
    results = await orchestrator.execute_all()
    
    print("4. Evaluating SLOs...")
    slos = await slo_engine.evaluate_all()
    
    print("5. Evaluating Correlation and Policy...")
    correlation_ctx = correlation_engine.correlate_failures(results)
    decision = policy_engine.evaluate_policy(settings.ENVIRONMENT, results, slos)

    print("\n[✔] TEST COMPLETE")
    print(f"Policy Decision: {decision.action.value} ({decision.reason})")
    print(f"Correlated Root Cause: {correlation_ctx.root_cause_identified}")
    
    for r in results:
        print(f"  - {r.check_type}: {r.status.value} ({r.latency_sec}s)")

if __name__ == "__main__":
    asyncio.run(main())
