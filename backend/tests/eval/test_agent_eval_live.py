"""Opt-in live agent eval.

Runs the golden prompt set against a running stack + seeded tenant and scores
each answer with the rubric. Skipped by default because it needs a live backend,
a seeded tenant, and LLM budget.

Enable with:

    AETHOS_EVAL_LIVE=1 \
    AETHOS_EVAL_API_URL=http://localhost:8011 \
    AETHOS_EVAL_TOKEN=<jwt> \
    AETHOS_EVAL_TENANT_ID=<uuid> \
    uv run pytest tests/eval/test_agent_eval_live.py -q -s
"""

from __future__ import annotations

import os

import pytest

from app.evals.golden_prompts import GOLDEN_CASES
from app.evals.runner import run_case

_LIVE = os.getenv("AETHOS_EVAL_LIVE") == "1"
_API_URL = os.getenv("AETHOS_EVAL_API_URL", "http://localhost:8011")
_TOKEN = os.getenv("AETHOS_EVAL_TOKEN", "")
_TENANT = os.getenv("AETHOS_EVAL_TENANT_ID", "")

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not (_LIVE and _TOKEN and _TENANT),
        reason="set AETHOS_EVAL_LIVE=1 + AETHOS_EVAL_TOKEN + AETHOS_EVAL_TENANT_ID to run",
    ),
]


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=lambda c: c.id)
async def test_golden_case(case) -> None:
    result = await run_case(
        case, api_url=_API_URL, token=_TOKEN, tenant_id=_TENANT
    )
    print(result.summary)
    assert result.passed, result.summary
