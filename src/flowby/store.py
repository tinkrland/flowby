"""bytes by digest: the other half of an asset.

a board element holds `asset="sha256:<64 hex>"` and nothing else, which is the right thing for a
scene to hold and leaves one question open: where are the bytes. this is the answer, and it is the
smallest one that can be trusted. a file is stored under the hash of its own contents, so

    - the same file dropped twice is one file, and a re-import is a no-op
    - a digest that does not match its bytes cannot be stored, so a name can never lie about contents
    - a path that tries to climb out of the store is not a digest and never reaches the disk
    - a half-written file never has its final name, so a crash leaves nothing a reader could open

it knows nothing about boards, presets or the web. that is deliberate: the store is what the worker
will read from too, and a store that knows about the UI would have to be unpicked before it could.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path

DIGEST = re.compile(r"^sha256:([0-9a-f]{64})$")

# the biggest single object the store will take. intake.mjs refuses 25 MB in the browser, and this
# is the same limit said again on the side that cannot be bypassed by editing a page.
MAX_BYTES = 25 * 1024 * 1024


class StoreRefused(Exception):
    """what was asked of the store cannot be done, and the message says which part."""


def digest_of(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


class Store:
    def __init__(self, root: str | os.PathLike):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # -- the only place a digest becomes a path -----------------------------------------------

    def _path(self, digest: str) -> Path:
        match = DIGEST.match(str(digest))
        if not match:
            raise StoreRefused(f"{str(digest)[:40]!r} is not a sha256 digest, so it names no file")
        hexed = match.group(1)
        # two levels of fan-out, so a store with a hundred thousand files is not one directory
        return self.root / hexed[:2] / hexed[2:4] / hexed

    # -- write ---------------------------------------------------------------------------------

    def put(self, data: bytes, expect: str | None = None) -> str:
        """store bytes and return their digest. `expect` is a digest the caller was told, if any."""
        if not isinstance(data, (bytes, bytearray)):
            raise StoreRefused("only bytes can be stored")
        if not data:
            raise StoreRefused("an empty file is not an asset")
        if len(data) > MAX_BYTES:
            raise StoreRefused(f"{len(data) / 1048576:.1f} MB is over the {MAX_BYTES // 1048576} MB limit")
        actual = digest_of(bytes(data))
        if expect is not None and expect != actual:
            raise StoreRefused(f"these bytes hash to {actual[:19]}…, not the {str(expect)[:19]}… they were sent under")
        target = self._path(actual)
        if target.exists():
            return actual  # the same file twice is one file
        target.parent.mkdir(parents=True, exist_ok=True)
        # write beside the target and rename: a rename is atomic, so the final name never holds a
        # partial file, and two writers of the same bytes cannot corrupt each other
        fd, temp = tempfile.mkstemp(dir=target.parent, prefix=".part-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, target)
        except BaseException:
            try:
                os.unlink(temp)
            except FileNotFoundError:
                pass
            raise
        return actual

    # -- read ----------------------------------------------------------------------------------

    def has(self, digest: str) -> bool:
        try:
            return self._path(digest).is_file()
        except StoreRefused:
            return False

    def get(self, digest: str) -> bytes:
        path = self._path(digest)
        if not path.is_file():
            raise StoreRefused(f"{digest[:19]}… is not in the store")
        data = path.read_bytes()
        # a file that was edited, truncated or bit-rotted is not the file its name promises. serving
        # it would make every digest a guess, so it is refused and said so.
        if digest_of(data) != digest:
            raise StoreRefused(f"{digest[:19]}… is on disk but its bytes no longer hash to it")
        return data

    def size(self, digest: str) -> int:
        path = self._path(digest)
        if not path.is_file():
            raise StoreRefused(f"{digest[:19]}… is not in the store")
        return path.stat().st_size

    def count(self) -> int:
        return sum(1 for p in self.root.rglob("*") if p.is_file() and not p.name.startswith(".part-"))

    def verify(self) -> list[str]:
        """every digest whose file no longer matches its name. an empty list is a healthy store."""
        bad = []
        for path in self.root.rglob("*"):
            if not path.is_file() or path.name.startswith(".part-"):
                continue
            if "sha256:" + path.name != digest_of(path.read_bytes()):
                bad.append("sha256:" + path.name)
        return sorted(bad)
