import yaml
from typing import Dict, List
from app.engine.models import CheckResultDTO, SLOStateDTO, PolicyDecisionDTO, PolicyAction, Severity

class PolicyEngine:
    """Enforces block/allow rules based on severity and budget configurations."""
    
    def __init__(self, policy_path: str):
        self.policy_path = policy_path
        self.rules = self._load_rules()
        
    def _load_rules(self) -> Dict:
        try:
            with open(self.policy_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            # Fallback permissive config if file is missing
            return {"decisions": {"deploy_gate_mode": "permissive"}, "checks": {}}

    def evaluate_policy(self, environment: str, check_results: List[CheckResultDTO], slo_state: Dict[str, SLOStateDTO]) -> PolicyDecisionDTO:
        # Check SLO states
        for service_id, state in slo_state.items():
            if state.decision == "budget_exhausted":
                return PolicyDecisionDTO(
                    action=PolicyAction.BLOCK,
                    reason=f"SLO budget exhausted for {service_id}"
                )
            if state.decision == "unknown":
                from app.utils.logger import setup_logger
                logger = setup_logger(__name__)
                logger.warning(f"Fail-open policy allowance for {service_id} due to degraded UNKNOWN SLO state.")
                

        # Check individual required domain results
        for res in check_results:
            rule = self.rules.get("checks", {}).get(res.check_type, {})
            is_required = rule.get("required", False)
            severity = rule.get("severity", "WARNING")
            
            # Use configured severity if available, otherwise fallback to check's reported severity
            actual_severity = Severity(severity) if severity in ["CRITICAL", "WARNING", "INFO"] else res.severity
            
            if res.status == "unhealthy":
                if is_required or actual_severity == Severity.CRITICAL:
                    return PolicyDecisionDTO(
                        action=PolicyAction.BLOCK,
                        reason=f"Failed required check: {res.check_type} at severity {actual_severity.value}"
                    )
        
        # Determine if there are warnings
        warnings = [r for r in check_results if r.status != "healthy"]
        if warnings:
            if self.rules.get("decisions", {}).get("allow_partial_degradation") is False:
                 return PolicyDecisionDTO(
                     action=PolicyAction.BLOCK,
                     reason=f"{len(warnings)} non-healthy checks but partial degradation is disabled"
                 )
            return PolicyDecisionDTO(action=PolicyAction.WARN, reason="Passed with warnings for optional checks")
            
        return PolicyDecisionDTO(action=PolicyAction.ALLOW, reason="All checks passed successfully")
