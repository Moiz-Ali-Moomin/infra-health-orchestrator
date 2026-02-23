import time
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException
from app.utils.logger import setup_logger
from app.config import settings

logger = setup_logger(__name__)

class KubernetesCheck:
    """Validates Pods and Deployments in a Kubernetes namespace."""
    
    @staticmethod
    def _init_k8s():
        try:
            k8s_config.load_incluster_config()
            return True
        except k8s_config.ConfigException:
            try:
                k8s_config.load_kube_config()
                return True
            except Exception as e:
                logger.error(f"Failed to load Kubernetes configuration: {e}")
                return False
                
        # Inject global connection timeout to prevent hanging when cluster is unreachable
        k8s_client_config = client.Configuration.get_default_copy()
        k8s_client_config.retries = 1
        client.Configuration.set_default(k8s_client_config)
        return True

    @classmethod
    def run(cls) -> dict:
        logger.info("Running Kubernetes health check...")
        start_time = time.time()
        
        if not cls._init_k8s():
            return {"status": "unhealthy", "details": "K8s Config Load Failed", "latency_sec": 0.0}

        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        namespace = settings.KUBERNETES_NAMESPACE
        
        all_passed = True
        details = {}
        
        # Validate Pods
        try:
            pods = v1.list_namespaced_pod(namespace, _request_timeout=(5, 5))
            failing_pods = []
            
            for pod in pods.items:
                pod_name = pod.metadata.name
                phase = pod.status.phase
                
                if phase in ["Failed", "Unknown"]:
                    failing_pods.append(f"{pod_name} (Phase: {phase})")
                    all_passed = False
                    
                if pod.status.container_statuses:
                    for status in pod.status.container_statuses:
                        if status.state.waiting and status.state.waiting.reason == "CrashLoopBackOff":
                            failing_pods.append(f"{pod_name}:{status.name} (CrashLoopBackOff)")
                            all_passed = False
                            
            if failing_pods:
                details['pods'] = failing_pods
            else:
                details['pods'] = "All Pods Healthy"
                
        except ApiException as e:
            logger.error(f"K8s API Exception (Pods): {e}")
            details['pods'] = f"API Error: {e}"
            all_passed = False

        # Validate Deployments
        try:
            deployments = apps_v1.list_namespaced_deployment(namespace, _request_timeout=(5, 5))
            failing_deploys = []
            
            for deploy in deployments.items:
                deploy_name = deploy.metadata.name
                desired = deploy.spec.replicas or 0
                ready = deploy.status.ready_replicas or 0
                
                if desired > 0 and ready < desired:
                    failing_deploys.append(f"{deploy_name} ({ready}/{desired} ready)")
                    all_passed = False
                    
            if failing_deploys:
                details['deployments'] = failing_deploys
            else:
                details['deployments'] = "All Deployments Ready"
                
        except ApiException as e:
            logger.error(f"K8s API Exception (Deployments): {e}")
            details['deployments'] = f"API Error: {e}"
            all_passed = False
            
        latency = time.time() - start_time
        status = "healthy" if all_passed else "unhealthy"
        
        if all_passed:
            logger.info("Kubernetes health check passed.")
        else:
            logger.error("Kubernetes health check failed.")
            
        return {
            "status": status,
            "details": details,
            "latency_sec": round(latency, 3)
        }
