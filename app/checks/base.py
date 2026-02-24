from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.engine.models import CheckResultDTO, CheckStatus, Severity

class BaseCheck(ABC):
    """Abstract interface for all validation checks."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the check domain."""
        pass

    @abstractmethod
    async def run(self, **kwargs) -> CheckResultDTO:
        """Executes the specific validation and returns a standardized DTO."""
        pass

    def build_result(
        self,
        status: CheckStatus,
        latency_sec: float,
        details: Dict[str, Any] = None,
        severity: Severity = Severity.WARNING,
        cluster: str = "local",
        error_message: Optional[str] = None
    ) -> CheckResultDTO:
        """Helper to construct the valid DTO."""
        return CheckResultDTO(
            check_type=self.name,
            status=status,
            latency_sec=latency_sec,
            details=details or {},
            severity=severity,
            cluster=cluster,
            error_message=error_message
        )
