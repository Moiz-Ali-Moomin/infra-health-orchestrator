from abc import ABC, abstractmethod
from typing import Dict, Any
from app.engine.models import ValidationRunDTO

class ValidationRepositoryInterface(ABC):
    @abstractmethod
    async def save_run(self, run_data: ValidationRunDTO) -> None:
        """Persists a snapshot of an execution."""
        pass

    @abstractmethod
    async def get_historical_stats(self, service_id: str, time_window_days: int) -> Dict[str, Any]:
        """Retrieves history for SLO burn rate calculations."""
        pass
