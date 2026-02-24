from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"

class CheckStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class PolicyAction(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    WARN = "WARN"

class CheckResultDTO(BaseModel):
    check_type: str
    status: CheckStatus
    latency_sec: float
    cluster: str = "local"
    severity: Severity = Severity.WARNING
    details: Dict[str, Any] = {}
    error_message: Optional[str] = None

class SLOStateDTO(BaseModel):
    availability_7d: float
    target: float
    burn_rate: float
    decision: str

class PolicyDecisionDTO(BaseModel):
    action: PolicyAction
    reason: str

class CorrelationContextDTO(BaseModel):
    root_cause_identified: Optional[str]
    impacted_dependencies: List[str]

class ValidationRunDTO(BaseModel):
    run_id: str
    correlation_id: str
    environment: str
    
    # Non-Repudiation
    caller_identity: str
    caller_role: str
    caller_ip: Optional[str] = None
    trigger_source: str
    status: str
    policy_decision: PolicyDecisionDTO
    correlation_summary: CorrelationContextDTO
    slo_state: Dict[str, SLOStateDTO] = {}
    details: Dict[str, CheckResultDTO] = {}
    latency_sec: float
    timestamp: datetime
