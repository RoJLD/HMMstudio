"""Shared fixtures and markers for the validation suite.

This conftest is *separate* from the one in ``tests/``. The validation
suite is intentionally not run by the default ``pytest`` invocation (which
uses ``testpaths = ['tests']`` in pyproject.toml). Run it explicitly with
``pytest validation/``.
"""

from __future__ import annotations

import numpy as np
import pytest


def pytest_configure(config):
    """Register validation-specific markers."""
    config.addinivalue_line(
        "markers",
        "validation: scientific validation test (model correctness, not code correctness)",
    )
    config.addinivalue_line(
        "markers",
        "slow: validation test that may take >10s (recovery tests with N=10000)",
    )


# Auto-mark every test in this directory with @pytest.mark.validation
def pytest_collection_modifyitems(config, items):
    for item in items:
        item.add_marker(pytest.mark.validation)


@pytest.fixture(scope="session")
def rng_seed() -> int:
    """Canonical seed used across the suite for reproducibility."""
    return 42


@pytest.fixture
def rng(rng_seed: int) -> np.random.Generator:
    """Per-test rng seeded canonically."""
    return np.random.default_rng(rng_seed)
