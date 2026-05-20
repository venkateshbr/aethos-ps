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
from app.workers.autonomy_promoter import autonomy_promoter_worker
from app.workers.collections import collections_worker
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
        collections_worker,
        autonomy_promoter_worker,
    ]

    cron_jobs: ClassVar[list] = [
        # FX refresh: daily at 08:00 UTC.
        cron(
            fx_refresh_worker,
            hour={8},
            minute={0},
            run_at_startup=False,
        ),
        # Dunning emails: daily at 06:00 UTC.
        cron(
            collections_worker,
            hour={6},
            minute={0},
            run_at_startup=False,
        ),
        # Autonomy promoter: daily at 02:00 UTC.
        cron(
            autonomy_promoter_worker,
            hour={2},
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
    job_timeout: int = 300
