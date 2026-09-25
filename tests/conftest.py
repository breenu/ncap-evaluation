"""Shared test fixtures.

Every dataset created in tests/ is SYNTHETIC: small, made-up values written to
pytest's temporary directories to exercise a rule. None of it is real data, and
none of it is ever written into data/ (CLAUDE.md hard rule 1).
"""

from pathlib import Path

import pytest


@pytest.fixture
def fake_fetch():
    """A stand-in for http_fetch that writes given bytes instead of using the network.

    SYNTHETIC. Usage: fetch = fake_fetch(b"payload"); fetch.calls counts invocations.
    """

    def make(payload: bytes):
        def fetch(url: str, dest: Path) -> None:
            fetch.calls += 1
            dest.write_bytes(payload)

        fetch.calls = 0
        return fetch

    return make
