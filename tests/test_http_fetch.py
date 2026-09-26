"""Resumable HTTP download. The server here is a SYNTHETIC in-memory fake that can drop
the connection mid-file and honours (or ignores) Range headers."""

import pytest
import requests

from src.common.manifest import IncompleteDownload, http_fetch

PAYLOAD = bytes(range(256)) * 40  # 10,240 synthetic bytes


class FakeResponse:
    def __init__(self, status, body, headers, drop_after=None):
        self.status_code, self._body, self.headers, self._drop = status, body, headers, drop_after

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        if self.status_code >= 400 and self.status_code != 416:
            raise requests.HTTPError(str(self.status_code))

    def iter_content(self, chunk_size):
        sent = 0
        for i in range(0, len(self._body), 1000):
            if self._drop is not None and sent >= self._drop:
                raise requests.exceptions.ChunkedEncodingError("connection reset")
            yield self._body[i : i + 1000]
            sent += 1000


class FakeServer:
    """Serves PAYLOAD. drops: list of byte counts after which successive requests die."""

    def __init__(self, drops=(), honour_range=True):
        self.drops, self.honour_range, self.requests = list(drops), honour_range, []

    def get(self, url, stream, timeout, headers):
        self.requests.append(headers.get("Range"))
        drop = self.drops.pop(0) if self.drops else None
        rng = headers.get("Range")
        if rng and self.honour_range:
            start = int(rng.split("=")[1].rstrip("-"))
            if start >= len(PAYLOAD):
                return FakeResponse(416, b"", {"Content-Range": f"bytes */{len(PAYLOAD)}"})
            body = PAYLOAD[start:]
            cr = f"bytes {start}-{len(PAYLOAD) - 1}/{len(PAYLOAD)}"
            return FakeResponse(206, body, {"Content-Range": cr}, drop)
        return FakeResponse(200, PAYLOAD, {"Content-Length": str(len(PAYLOAD))}, drop)


def test_resumes_after_dropped_connections(tmp_path):
    server = FakeServer(drops=[3000, 2000])
    dest = tmp_path / "f.part"
    http_fetch("u", dest, session=server, sleep=lambda s: None)
    assert dest.read_bytes() == PAYLOAD
    assert server.requests == [None, "bytes=3000-", "bytes=5000-"]


def test_restarts_when_server_ignores_range(tmp_path):
    server = FakeServer(drops=[3000], honour_range=False)
    dest = tmp_path / "f.part"
    http_fetch("u", dest, session=server, sleep=lambda s: None)
    assert dest.read_bytes() == PAYLOAD  # not 3000 stale bytes + a full copy


def test_already_complete_partial_is_accepted(tmp_path):
    dest = tmp_path / "f.part"
    dest.write_bytes(PAYLOAD)
    http_fetch("u", dest, session=FakeServer(), sleep=lambda s: None)
    assert dest.read_bytes() == PAYLOAD


def test_gives_up_after_attempts_and_keeps_bytes(tmp_path):
    server = FakeServer(drops=[1000, 0, 0])
    dest = tmp_path / "f.part"
    with pytest.raises((requests.exceptions.ChunkedEncodingError, IncompleteDownload)):
        http_fetch("u", dest, attempts=3, session=server, sleep=lambda s: None)
    assert dest.read_bytes() == PAYLOAD[:1000]  # progress kept for the next run
