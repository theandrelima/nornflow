"""Performance smoke tests for output masking."""

import time

import pytest

from nornflow.masking import LARGE_TEXT_THRESHOLD, REDACTED, mask_structure, mask_text

# Smoke thresholds — catch order-of-magnitude regressions, not microsecond noise.
# 100 KB regex pass is dominated by the large keyword alternation pattern (~100-250 ms
# with underscore/hyphen/dot surface forms).
_MASK_TEXT_100KB_MAX_S = 0.25
_MASK_TEXT_LARGE_BLOB_NO_KEYWORDS_MAX_S = 0.002
_MASK_STRUCTURE_CONFIG_MAX_S = 0.005

_NORNIR_CONFIG_FIXTURE = {
    "inventory": {
        "plugin": "NautobotInventory",
        "options": {
            "nautobot_url": "http://localhost:8080",
            "nautobot_token": "3ff4118f836dfa3c2fc1b4bc0db7afccfb87dcd3",
        },
    },
    "runner": {"plugin": "threaded", "options": {"num_workers": 5}},
    "logging": {"level": "DEBUG"},
}


def _p99_seconds(samples: list[float]) -> float:
    """Return approximate p99 from a list of elapsed times."""
    ordered = sorted(samples)
    index = min(len(ordered) - 1, int(len(ordered) * 0.99))
    return ordered[index]


class TestMaskingPerformance:
    """Guard against order-of-magnitude masking regressions."""

    def test_mask_text_small_line(self):
        text = "password=secret123 hostname=router1"
        samples = []
        for _ in range(100):
            start = time.perf_counter()
            mask_text(text)
            samples.append(time.perf_counter() - start)
        assert _p99_seconds(samples) < 0.001

    def test_mask_text_100kb_with_secret(self):
        text = "x" * 100_000 + " password=secret123"
        samples = []
        for _ in range(20):
            start = time.perf_counter()
            result = mask_text(text)
            samples.append(time.perf_counter() - start)
        assert REDACTED in result
        assert _p99_seconds(samples) < _MASK_TEXT_100KB_MAX_S

    def test_mask_text_large_blob_without_keywords_is_fast(self):
        text = "y" * (LARGE_TEXT_THRESHOLD + 50_000)
        mask_text(text)  # warmup substring pre-check path
        samples = []
        for _ in range(20):
            start = time.perf_counter()
            assert mask_text(text) == text
            samples.append(time.perf_counter() - start)
        assert _p99_seconds(samples) < _MASK_TEXT_LARGE_BLOB_NO_KEYWORDS_MAX_S

    def test_mask_structure_nornir_config(self):
        samples = []
        for _ in range(50):
            start = time.perf_counter()
            result = mask_structure(_NORNIR_CONFIG_FIXTURE)
            samples.append(time.perf_counter() - start)
        assert result["inventory"]["options"]["nautobot_token"] == REDACTED
        assert _p99_seconds(samples) < _MASK_STRUCTURE_CONFIG_MAX_S
