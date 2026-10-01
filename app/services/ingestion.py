from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.persistence.entities import IngestionJobRecord, utcnow
from app.persistence.repositories import IngestionJobRepository


class IngestionStateError(ValueError):
    """Raised when an ingestion job attempts an invalid lifecycle transition."""


class IngestionService:
    """Enforce worker-safe ingestion lifecycle rules.

    The repository adapter is responsible for atomic compare-and-set behavior in
    production. The in-memory adapter provides the same state contract for tests.
    """

    ACTIVE = "PROCESSING"
    PENDING = "PENDING"
    READY = "READY"
    FAILED = "FAILED"

    def __init__(self, jobs: IngestionJobRepository) -> None:
        self.jobs = jobs

    def claim(
        self,
        *,
        job_id: str,
        organization_id: str,
        lease_seconds: int = 300,
        now: datetime | None = None,
    ) -> IngestionJobRecord:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive.")

        job = self._get(job_id, organization_id)
        current = now or utcnow()

        if job.status == self.ACTIVE and job.lease_until is not None:
            if job.lease_until > current:
                raise IngestionStateError("Job is already leased for processing.")
        elif job.status not in {self.PENDING, self.FAILED}:
            raise IngestionStateError(
                f"Job cannot be claimed from state {job.status!r}."
            )

        job.status = self.ACTIVE
        job.attempt_count += 1
        job.lease_until = current + timedelta(seconds=lease_seconds)
        job.last_error = None
        job.updated_at = current
        return self.jobs.update(job)

    def complete(
        self,
        *,
        job_id: str,
        organization_id: str,
        now: datetime | None = None,
    ) -> IngestionJobRecord:
        job = self._get(job_id, organization_id)
        self._require_processing(job)
        current = now or utcnow()
        job.status = self.READY
        job.lease_until = None
        job.last_error = None
        job.updated_at = current
        return self.jobs.update(job)

    def fail(
        self,
        *,
        job_id: str,
        organization_id: str,
        error: str,
        now: datetime | None = None,
    ) -> IngestionJobRecord:
        if not error.strip():
            raise ValueError("error is required.")
        job = self._get(job_id, organization_id)
        self._require_processing(job)
        current = now or utcnow()
        job.status = self.FAILED
        job.lease_until = None
        job.last_error = error[:4000]
        job.updated_at = current
        return self.jobs.update(job)

    def retry_expired(
        self,
        *,
        job_id: str,
        organization_id: str,
        now: datetime | None = None,
    ) -> IngestionJobRecord:
        job = self._get(job_id, organization_id)
        current = now or utcnow()
        if job.status != self.ACTIVE:
            raise IngestionStateError("Only PROCESSING jobs can expire.")
        if job.lease_until is None or job.lease_until > current:
            raise IngestionStateError("Job lease has not expired.")
        job.status = self.PENDING
        job.lease_until = None
        job.last_error = "Processing lease expired; job returned to PENDING."
        job.updated_at = current
        return self.jobs.update(job)

    def _get(self, job_id: str, organization_id: str) -> IngestionJobRecord:
        job = self.jobs.get(job_id, organization_id)
        if job is None:
            raise KeyError(f"Unknown ingestion job for organization: {job_id}")
        return job

    @staticmethod
    def _require_processing(job: IngestionJobRecord) -> None:
        if job.status != IngestionService.ACTIVE:
            raise IngestionStateError(
                f"Job must be PROCESSING, got {job.status!r}."
            )
