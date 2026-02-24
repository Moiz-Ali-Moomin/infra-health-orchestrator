import importlib
from typing import Dict
from app.checks.base import BaseCheck
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class PluginLoader:
    """Discovers and instantiates validation checks programmatically."""
    
    def __init__(self, cluster_registry=None):
        self.cluster_registry = cluster_registry
    
    def load_checks(self) -> Dict[str, BaseCheck]:
        # For simplicity, explicitly loading known checks instead of dynamic discovery
        # A true plugin system would os.walk the checks directory
        from app.checks.http_check import HttpCheck
        from app.checks.database_check import DatabaseCheck
        from app.checks.kubernetes_check import KubernetesCheck
        from app.checks.resource_check import ResourceCheck
        
        checks = [
            HttpCheck(),
            DatabaseCheck(),
            KubernetesCheck(cluster_registry=self.cluster_registry),
            ResourceCheck()
        ]
        
        plugin_map = {check.name: check for check in checks}
        logger.info(f"Loaded {len(plugin_map)} validation plugins. (HTTP, DB, K8s, Resource)")
        return plugin_map
