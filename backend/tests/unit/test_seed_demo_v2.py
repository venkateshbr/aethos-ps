from __future__ import annotations

import pytest

from scripts.seed_demo_v2 import _guard_reset_target

pytestmark = pytest.mark.unit


def test_demo_reset_rejects_nonmatching_tenant_name() -> None:
    with pytest.raises(ValueError, match="Refusing reset"):
        _guard_reset_target(
            actual_name="Sterling Bridge Advisory Group",
            required_name="Meridian Demo",
        )


def test_demo_reset_accepts_exact_tenant_name() -> None:
    _guard_reset_target(
        actual_name="Meridian Demo",
        required_name="Meridian Demo",
    )
