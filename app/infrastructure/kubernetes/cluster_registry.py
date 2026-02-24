from typing import Dict, Optional
from kubernetes import client, config
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class ClusterRegistry:
    """
    Principal-tier abstraction for Multi-Cluster API execution.
    Replaces static `load_incluster_config()` and `load_kube_config()` singletons
    with a dynamically routable mapping of cluster contexts to ApiClients.
    """
    
    def __init__(self):
        # Maps cluster_name -> client.ApiClient
        self.clients: Dict[str, client.ApiClient] = {}
        
    def register_cluster(self, name: str, kubeconfig_path: str, context: Optional[str] = None):
        try:
            # We initialize a new configuration explicitly bound to a specific context
            kube_config = client.Configuration()
            config.load_kube_config(
                config_file=kubeconfig_path, 
                context=context,
                client_configuration=kube_config
            )
            api_client = client.ApiClient(configuration=kube_config)
            self.clients[name] = api_client
            logger.info(f"Registered multi-cluster API client for: {name}")
        except Exception as e:
            logger.error(f"Failed to load cluster context {name}: {e}")
            
    def get_client(self, cluster_name: str) -> Optional[client.ApiClient]:
        return self.clients.get(cluster_name)
    
    def get_core_v1(self, cluster_name: str) -> Optional[client.CoreV1Api]:
        api_client = self.get_client(cluster_name)
        if api_client:
            return client.CoreV1Api(api_client)
        return None

    def get_apps_v1(self, cluster_name: str) -> Optional[client.AppsV1Api]:
        api_client = self.get_client(cluster_name)
        if api_client:
            return client.AppsV1Api(api_client)
        return None
