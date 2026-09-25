"""Read-only, seekable file object over HTTP range requests.

Lets pyarrow read a remote Parquet file's footer and selected column chunks
without downloading the whole file (used by the step 0 probe to measure a
dataset before deciding to download it)."""

import io

from src.common.manifest import _session


class HTTPRangeFile(io.RawIOBase):
    def __init__(self, url: str):
        self.s = _session()
        r = self.s.head(url, allow_redirects=True, timeout=(30, 60))
        r.raise_for_status()
        self.url = r.url  # follow the redirect once (GitHub -> object store)
        self.size = int(r.headers["Content-Length"])
        self.pos = 0
        self.bytes_fetched = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.pos, io.SEEK_END: self.size}[whence]
        self.pos = base + offset
        return self.pos

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        end = min(self.pos + n, self.size) - 1
        r = self.s.get(self.url, headers={"Range": f"bytes={self.pos}-{end}"}, timeout=(30, 300))
        r.raise_for_status()
        data = r.content
        self.pos += len(data)
        self.bytes_fetched += len(data)
        return data

    def readinto(self, b) -> int:
        data = self.read(len(b))
        b[: len(data)] = data
        return len(data)
