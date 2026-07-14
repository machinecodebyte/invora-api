from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class JobListQuery:
    user_id: UUID
    job_type: str | None
    status: str | None
    entity_id: UUID | None
    queue_name: str | None
    date_from: datetime | None
    date_to: datetime | None
    limit: int
    offset: int
    sort_by: str
    sort_order: str
