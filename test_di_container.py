from app.containers import Container
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

if __name__ == "__main__":
    logger.info("Initializing DI Container...")
    container = Container()
    
    # Force evaluation of singletons
    logger.info("Resolving Repositories...")
    repo = container.validation_repo()
    
    logger.info("Resolving SLO Engine...")
    slo = container.slo_engine()
    
    logger.info("Resolving Correlation Engine...")
    corr = container.correlation_engine()
    
    logger.info("Resolving Plugin Loader...")
    loader = container.plugin_loader()
    
    logger.info("Resolving Orchestrator...")
    orchestrator = container.orchestrator()
    
    logger.info("ALL PRINCIPAL-TIER INVERSIONS OF CONTROL SUCCEEDED.")
