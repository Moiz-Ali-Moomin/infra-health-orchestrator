from dependency_injector import containers, providers
from app.config import Settings
from app.repositories.validation_repo import SQLValidationRepository
from app.infrastructure.database.session import AsyncSessionFactory
from app.infrastructure.cache.redis_client import init_redis_pool
from app.engine.plugin_loader import PluginLoader
from app.engine.policy_engine import PolicyEngine
from app.engine.slo_engine import SLOEngine
from app.engine.correlation_engine import CorrelationEngine
from app.engine.orchestrator import Orchestrator
from app.utils.circuit_breaker import CircuitBreakerFactory # We will define this next

class Container(containers.DeclarativeContainer):
    """
    Principal-tier IoC Container providing application dependencies 
    to all sub-routers and engines to eliminate global state.
    """
    
    # Configuration
    config = providers.Configuration(pydantic_settings=[Settings()])
    
    # Core Infrastructure
    session_factory = providers.Object(AsyncSessionFactory)
    
    redis_pool = providers.Resource(
        init_redis_pool,
        url=config.REDIS_URL
    )
    
    # Repositories
    validation_repo = providers.Singleton(
        SQLValidationRepository,
        session_factory=session_factory
    )
    
    # Utilities
    circuit_breaker_factory = providers.Factory(
        CircuitBreakerFactory,
        redis_client=redis_pool
    )
    
    # Core Engines
    policy_engine = providers.Singleton(
        PolicyEngine,
        policy_path=config.POLICY_PATH
    )
    
    slo_engine = providers.Singleton(
        SLOEngine,
        slo_path=config.SLO_PATH,
        repo=validation_repo
    )
    
    correlation_engine = providers.Singleton(
        CorrelationEngine,
        topology_path=config.TOPOLOGY_PATH
    )
    
    from app.infrastructure.kubernetes.cluster_registry import ClusterRegistry
    
    cluster_registry = providers.Singleton(ClusterRegistry)
    
    # Plugin Context
    plugin_loader = providers.Singleton(
        PluginLoader,
        cluster_registry=cluster_registry
    )
    
    # Root Orchestrator
    orchestrator = providers.Factory(
        Orchestrator,
        plugin_loader=plugin_loader,
        circuit_breaker_factory=circuit_breaker_factory,
        max_concurrent=config.MAX_CONCURRENT_CHECKS,
        global_timeout=config.GLOBAL_TIMEOUT_SEC
    )
