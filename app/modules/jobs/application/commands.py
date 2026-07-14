from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ForecastJobEnqueueCommand:
    user_id: UUID
    forecast_run_id: UUID


@dataclass(frozen=True, slots=True)
class JobRetryCommand:
    user_id: UUID
    job_id: UUID


@dataclass(frozen=True, slots=True)
class JobCancelCommand:
    user_id: UUID
    job_id: UUID
