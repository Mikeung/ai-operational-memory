import logging
from collections.abc import Callable
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class OperationalScheduler:
    """Runs periodic scan jobs in a background thread.

    Single-process. Observable. No distributed workers.
    """

    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler(timezone="UTC", daemon=True)

    def register_scan(
        self,
        scan_func: Callable[[str], Any],
        targets: list[str],
        interval_seconds: int,
    ) -> None:
        for target in targets:
            job_id = f"scan_{abs(hash(target))}"
            self._scheduler.add_job(
                scan_func,
                trigger=IntervalTrigger(seconds=interval_seconds),
                args=[target],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=60,
                coalesce=True,
            )
            logger.info(
                "Scan job registered",
                extra={
                    "target": target,
                    "interval_s": interval_seconds,
                    "job_id": job_id,
                },
            )

    def start(self) -> None:
        self._scheduler.start()
        logger.info(
            "Scheduler started",
            extra={"job_count": len(self._scheduler.get_jobs())},
        )

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def get_jobs_info(self) -> list[dict[str, Any]]:
        return [
            {
                "id": job.id,
                "next_run": str(job.next_run_time),
                "trigger": str(job.trigger),
            }
            for job in self._scheduler.get_jobs()
        ]
