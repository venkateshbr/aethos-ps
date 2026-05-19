"""ARQ worker settings — registered functions and cron schedule.

Start a worker locally:
    uv run arq app.workers.arq_settings.WorkerSettings

The worker connects to Upstash Redis (or local Redis if ``upstash_redis_url``
is empty) and processes enqueued jobs + runs cron jobs on schedule.
"""

from __future__ import annotations

from typing import ClassVar

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.document_extraction import extract_document_worker
from app.workers.fx_refresh import fx_refresh_worker


class WorkerSettings:
    """ARQ worker configuration class.

    ``functions`` — tasks enqueued imperatively via ``ArqRedis.enqueue_job()``.
    ``cron_jobs`` — tasks run on a schedule; worker evaluates these every minute.
    """

    functions: ClassVar[list] = [
        fx_refresh_worker,
        extract_document_worker,
    ]

    cron_jobs: ClassVar[list] = [
        # Run FX refresh daily at 08:00 UTC.
        # run_at_startup=False: don't fetch rates the moment the worker boots —
        # the daily schedule is sufficient unless manually triggered.
        cron(
            fx_refresh_worker,
            hour={8},
            minute={0},
            run_at_startup=False,
        ),
    ]

    redis_settings: RedisSettings = RedisSettings.from_dsn(
        settings.upstash_redis_url or "redis://localhost:6379"
    )

    # Maximum concurrent jobs across all queues.
    max_jobs: int = 10

    # Seconds before a job is considered timed out and marked failed.
    job_timeout: int = 120
