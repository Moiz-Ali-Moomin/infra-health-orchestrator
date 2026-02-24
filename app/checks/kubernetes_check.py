import time
import asyncio
from typing import Optional
from kubernetes.client.rest import ApiException
from app.utils.logger import setup_logger
from app.config import settings
from app.checks.base import BaseCheck
from app.engine.models import CheckResultDTO, CheckStatus, Severity
from app.infrastructure.kubernetes.cluster_registry import ClusterRegistry

logger = setup_logger(__name__)

class KubernetesCheck(BaseCheck):
    """Validates Pods and Deployments in a Kubernetes namespace across multi-cluster targets."""
    
    def __init__(self, cluster_registry: Optional[ClusterRegistry] = None):
        self.registry = cluster_registry
        
    @property
    def name(self) -> str:
        return "kubernetes_check"

    async def run(self, cluster_name: str = "local", **kwargs) -> CheckResultDTO:
        logger.info(f"Running Kubernetes health check against cluster: {cluster_name}")
        start_time = time.time()
        
        # Wrapping sync kubernetes client calls to avoid blocking loop
        def _get_k8s_state(target_cluster: str):
            if not self.registry:
                return None, None
                
            v1_api = self.registry.get_core_v1(target_cluster)
            apps_api = self.registry.get_apps_v1(target_cluster)
            
            if not v1_api or not apps_api:
                return None, None
                
            namespace = settings.KUBERNETES_NAMESPACE
            
            pods = None
            deploys = None
            try:
                pods = v1_api.list_namespaced_pod(namespace, _request_timeout=(5, 5))
            except ApiException as e:
                pods = e
                
            try:
                deploys = apps_api.list_namespaced_deployment(namespace, _request_timeout=(5, 5))
            except ApiException as e:
                deploys = e
                
            return pods, deploys

        pods, deployments = await asyncio.to_thread(_get_k8s_state, cluster_name)

        
        if pods is None and deployments is None:
            return self.build_result(
                status=CheckStatus.UNHEALTHY,
                latency_sec=0.0,
                details={"info": "K8s Config Load Failed"},
                severity=Severity.CRITICAL,
                error_message="Config Load Failed"
            )

        all_passed = True
        details = {}
        error_msg = []
        
        # Validate Pods
        if isinstance(pods, ApiException):
            logger.error(f"K8s API Exception (Pods): {pods}")
            details['pods'] = f"API Error: {pods}"
            all_passed = False
            error_msg.append("Pod API Error")
        else:
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
                error_msg.append("Failing Pods")
            else:
                details['pods'] = "All Pods Healthy"

        # Validate Deployments
        if isinstance(deployments, ApiException):
            logger.error(f"K8s API Exception (Deployments): {deployments}")
            details['deployments'] = f"API Error: {deployments}"
            all_passed = False
            error_msg.append("Deployment API Error")
        else:
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
                error_msg.append("Failing Deployments")
            else:
                details['deployments'] = "All Deployments Ready"
                
        latency = time.time() - start_time
        status = CheckStatus.HEALTHY if all_passed else CheckStatus.UNHEALTHY
        
        if all_passed:
            logger.info("Kubernetes health check passed.")
        else:
            logger.error("Kubernetes health check failed.")
            
        return self.build_result(
            status=status,
            latency_sec=round(latency, 3),
            details=details,
            severity=Severity.CRITICAL if not all_passed else Severity.INFO,
            cluster=cluster_name,
            error_message=" | ".join(error_msg) if error_msg else None
        )
