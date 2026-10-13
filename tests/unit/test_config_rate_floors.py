"""Pin the RATE_* fail-closed floors that the knobs suite leaves uncovered.

The three rate knobs are max(1, int(...)): a hand-edited 0 or negative would turn every
rate-limited route into a 500 rather than the refusal the operator presumably meant.
Nothing in tests/unit/test_config_knobs.py asserts these floors -- its PROBE string
never asks for them -- so a max(1, ...) -> max(0, ...) typo passes the whole suite.

These tests import config directly (no store, no fcntl) and drive the values through
os.environ + importlib.reload, so they run on any platform.
"""

import importlib
import os

import pytest


def _reload_with(**env: str):
    """Reload config with `env` applied over a CHAT_-clean baseline."""
    clean = {k: v for k, v in os.environ.items() if not k.startswith("CHAT_")}
    old = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(clean, **env)
        import config

        return importlib.reload(config)
    finally:
        os.environ.clear()
        os.environ.update(old)
        importlib.reload(importlib.import_module("config"))


@pytest.mark.parametrize("name", ["CHAT_RATE_READ", "CHAT_RATE_WRITE", "CHAT_RATE_ROOMS_PER_DAY"])
def test_rate_knobs_floor_at_one(name: str) -> None:
    """Zero and negatives clamp to 1; the bucket arithmetic divides by these."""
    cfg = _reload_with(**{name: "0"})
    attr = {"CHAT_RATE_READ": "RATE_READ", "CHAT_RATE_WRITE": "RATE_WRITE",
            "CHAT_RATE_ROOMS_PER_DAY": "RATE_ROOMS_PER_DAY"}[name]
    assert getattr(cfg, attr) == 1
    cfg = _reload_with(**{name: "-5"})
    assert getattr(cfg, attr) == 1


@pytest.mark.parametrize("name", ["CHAT_RATE_READ", "CHAT_RATE_WRITE", "CHAT_RATE_ROOMS_PER_DAY"])
def test_rate_knobs_refuse_junk(name: str) -> None:
    """int() raises at import, taking the process down -- the loudest bad-config report."""
    with pytest.raises(ValueError):
        _reload_with(**{name: "lots"})
