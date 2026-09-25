"""Anonymous listing of public S3 buckets over plain HTTPS (ListObjectsV2).

The OpenAQ archive and the ACAG satpmdata bucket are both public, so no AWS
credentials or boto3 are needed. The ETag returned here is recorded in each
raw manifest as the upstream version id.
"""

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass

from src.common.manifest import _session

_NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}


@dataclass(frozen=True)
class S3Object:
    key: str
    size: int
    etag: str
    last_modified: str


def bucket_url(bucket: str) -> str:
    return f"https://{bucket}.s3.amazonaws.com"


def object_url(bucket: str, key: str) -> str:
    return f"{bucket_url(bucket)}/{key}"


def _pages(bucket: str, prefix: str, delimiter: str | None) -> Iterator[ET.Element]:
    session = _session()
    params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
    if delimiter:
        params["delimiter"] = delimiter
    while True:
        r = session.get(bucket_url(bucket), params=params, timeout=(30, 120))
        r.raise_for_status()
        root = ET.fromstring(r.content)
        yield root
        if root.findtext("s3:IsTruncated", namespaces=_NS) != "true":
            return
        params["continuation-token"] = root.findtext("s3:NextContinuationToken", namespaces=_NS)


def list_objects(bucket: str, prefix: str = "") -> Iterator[S3Object]:
    """Every object under prefix (recursive). Zero-byte folder markers are skipped."""
    for root in _pages(bucket, prefix, delimiter=None):
        for c in root.findall("s3:Contents", _NS):
            size = int(c.findtext("s3:Size", namespaces=_NS))
            key = c.findtext("s3:Key", namespaces=_NS)
            if size == 0 and key.endswith("/"):
                continue
            yield S3Object(
                key=key,
                size=size,
                etag=c.findtext("s3:ETag", namespaces=_NS).strip('"'),
                last_modified=c.findtext("s3:LastModified", namespaces=_NS),
            )


def list_prefixes(bucket: str, prefix: str = "") -> list[str]:
    """Immediate sub-'folders' of prefix."""
    out = []
    for root in _pages(bucket, prefix, delimiter="/"):
        out += [
            p.findtext("s3:Prefix", namespaces=_NS) for p in root.findall("s3:CommonPrefixes", _NS)
        ]
    return out
