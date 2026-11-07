"""an artifact is what a job hands back, and the dashboard's tab for it is the whole reason this exists.

the four wires say what flows *between* nodes. an artifact is what leaves the graph, and it is a
different question with a different answer: it needs a file extension, a mime type, a licence, a
provenance, and (for some of them) several files that only mean something together.

the case that forced this out of `compile.py` is a font. nobody wires a font into a paint step, so
it is not a fifth colour, and nothing upstream should be told it exists. but a font is the output a
user wants, it is not an image, and it is a bundle: the same glyph outlines leave as .otf, .ttf and
.woff, and a .woff on its own is a worse deliverable than the three. so an artifact has a `kind`
(what it is for), a `bundle` (the files that travel together) and a `source` (which board and job
made it), and the dashboard tabs are projections of those three.

    assets      what comes in    uploads, scans, references, a corpus
    artifacts   what comes out   this module
    boards      the spatial work that connects the two
    projects    the folder around all of it

only artifacts are defined here. assets and boards already exist as `Scene` and the asset digests.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

SHA = re.compile(r"^[0-9a-f]{64}$")

# every kind of output flowby knows how to name. `wire` is the dtype the thing travels on while it
# is still inside a graph, or None when it only exists after the graph (a font, a bundle).
KINDS = {
    "image": {"wire": "image", "label": "image", "primary": "png",
              "files": ("png",), "mime": {"png": "image/png"}},
    "video": {"wire": "video", "label": "video", "primary": "mp4",
              "files": ("mp4",), "mime": {"mp4": "video/mp4"}},
    "model": {"wire": "mesh", "label": "3d model", "primary": "glb",
              "files": ("glb",), "mime": {"glb": "model/gltf-binary"}},
    "text": {"wire": "text", "label": "text", "primary": "txt",
             "files": ("txt",), "mime": {"txt": "text/plain"}},
    # woff2 is deliberately absent. it needs brotli, which the browser pipeline does not have, and
    # fontasy's own woff2 button exports a .woff under that name. a kind that lists a file nothing
    # can produce is a promise the plan makes and the worker cannot keep.
    "font": {"wire": None, "label": "font", "primary": "otf",
             "files": ("otf", "ttf", "woff"),
             "mime": {"otf": "font/otf", "ttf": "font/ttf", "woff": "font/woff"}},
    "lettering": {"wire": None, "label": "lettering", "primary": "png",
                  "files": ("png", "svg"),
                  "mime": {"png": "image/png", "svg": "image/svg+xml"}},
    "lora": {"wire": None, "label": "style adapter", "primary": "safetensors",
             "files": ("safetensors",), "mime": {"safetensors": "application/octet-stream"}},
}

# the wire a given dtype becomes when a graph leaves through it. a mesh is a model, because "mesh"
# names the geometry on a wire and "model" names the deliverable.
FROM_WIRE = {kind["wire"]: name for name, kind in KINDS.items() if kind["wire"]}

# the dashboard's tabs. a tab is a question the user asks, not a table in a database.
TABS = ("projects", "boards", "assets", "artifacts")

# a font that is not a glyph set is a rumour. these are the codepoints a usable latin font needs
# before it can be called one, and the fontasy charset (101 characters) covers all of them.
LATIN_CORE = frozenset(
    list(range(0x41, 0x5B)) + list(range(0x61, 0x7B)) + list(range(0x30, 0x3A))
)


class ArtifactRefused(Exception):
    """what came back is not something that can be filed as an artifact, and the message says why."""


@dataclass(frozen=True)
class Source:
    """where an artifact came from. without it an output is an orphan in a folder."""

    board: str
    job: str
    plan_digest: str
    element: str | None = None
    variant: int | None = None
    preset: str | None = None

    def as_dict(self) -> dict:
        return {"board": self.board, "job": self.job, "plan_digest": self.plan_digest,
                "element": self.element, "variant": self.variant, "preset": self.preset}


@dataclass(frozen=True)
class FileRecord:
    ext: str
    sha256: str
    bytes: int

    def as_dict(self) -> dict:
        return {"ext": self.ext, "sha256": self.sha256, "bytes": self.bytes}


@dataclass
class Artifact:
    """one deliverable. it may be several files, and they are one thing in the dashboard."""

    id: str
    kind: str
    name: str
    source: Source
    files: tuple[FileRecord, ...]
    licence: str = ""
    meta: dict = field(default_factory=dict)  # glyph count, family name, dimensions
    simulated: bool = True  # true until bytes from a real worker have been checked

    @property
    def primary(self) -> FileRecord:
        wanted = KINDS[self.kind]["primary"]
        for record in self.files:
            if record.ext == wanted:
                return record
        return self.files[0]

    @property
    def total_bytes(self) -> int:
        return sum(record.bytes for record in self.files)

    @property
    def digest(self) -> str:
        """the identity of the whole bundle, independent of the order the files arrived in."""
        body = "|".join(f"{r.ext}:{r.sha256}" for r in sorted(self.files, key=lambda r: r.ext))
        return "art_" + hashlib.sha256(body.encode()).hexdigest()[:32]

    def as_dict(self) -> dict:
        return {
            "id": self.id, "kind": self.kind, "label": KINDS[self.kind]["label"], "name": self.name,
            "digest": self.digest, "files": [r.as_dict() for r in self.files],
            "bytes": self.total_bytes, "source": self.source.as_dict(),
            "licence": self.licence, "meta": dict(self.meta), "simulated": self.simulated,
        }


def kind_for_wire(dtype: str) -> str:
    """the artifact kind a graph produces when it ends on this wire."""
    try:
        return FROM_WIRE[dtype]
    except KeyError:
        raise ArtifactRefused(
            f"{dtype!r} is not a wire a graph can end on. the wires are {', '.join(sorted(FROM_WIRE))}."
        ) from None


def suffix_for_wire(dtype: str) -> str:
    return KINDS[kind_for_wire(dtype)]["primary"]


def check_file(kind: str, record: dict) -> FileRecord:
    spec = KINDS.get(kind)
    if spec is None:
        raise ArtifactRefused(f"{kind!r} is not an artifact kind. the kinds are {', '.join(KINDS)}.")
    ext = str(record.get("ext") or "").lower().lstrip(".")
    if ext not in spec["files"]:
        raise ArtifactRefused(
            f"a {spec['label']} is {', '.join(spec['files'])}, not .{ext or '?'}"
        )
    digest = str(record.get("sha256") or "")
    if not SHA.match(digest):
        raise ArtifactRefused(f".{ext} arrived without a sha256, so its bytes are a rumour")
    size = int(record.get("bytes") or 0)
    if size <= 0:
        raise ArtifactRefused(f".{ext} is zero bytes. a worker that crashed halfway looks exactly like this")
    return FileRecord(ext, digest, size)


def file_artifact(kind: str, name: str, records: list[dict], source: Source,
                  licence: str = "", meta: dict | None = None, simulated: bool = True) -> Artifact:
    """file a set of returned files as one artifact, or refuse and say which file is the problem."""
    if not records:
        raise ArtifactRefused(f"a {kind} with no files is not an artifact")
    files = tuple(check_file(kind, record) for record in records)
    seen = [f.ext for f in files]
    dupes = sorted({e for e in seen if seen.count(e) > 1})
    if dupes:
        raise ArtifactRefused(f"{', '.join('.' + d for d in dupes)} arrived twice in one {kind}")
    if KINDS[kind]["primary"] not in seen:
        raise ArtifactRefused(
            f"a {KINDS[kind]['label']} needs its .{KINDS[kind]['primary']} (the primary file). "
            f"only {', '.join('.' + e for e in seen)} arrived"
        )
    if kind == "font":
        check_font(meta or {})
    ident = "a_" + hashlib.sha256(f"{source.job}|{name}|{kind}".encode()).hexdigest()[:12]
    return Artifact(ident, kind, name, source, files, licence, dict(meta or {}), simulated)


def check_font(meta: dict) -> None:
    """a font that cannot set the word 'Hello 123' is a sketch, so say so before it is filed.

    `codepoints` is what the glyph set actually mapped. a hand-lettered sheet that only produced
    uppercase is still a font, but it is a partial one, and the dashboard says partial.
    """
    if not meta.get("family"):
        raise ArtifactRefused("a font needs a family name, or every app will list it as 'Untitled'")
    codepoints = meta.get("codepoints")
    if codepoints is None:
        raise ArtifactRefused("a font must say which codepoints it maps; the glyph count alone is not enough")
    if not codepoints:
        raise ArtifactRefused("this font maps no codepoints")


def coverage(meta: dict) -> dict:
    """what share of a basic latin font this one covers, for the dashboard's 'partial' badge."""
    mapped = {int(c) for c in meta.get("codepoints") or []}
    have = len(LATIN_CORE & mapped)
    missing_groups = []
    groups = {"uppercase": range(0x41, 0x5B), "lowercase": range(0x61, 0x7B), "digits": range(0x30, 0x3A)}
    for name, span in groups.items():
        if not all(c in mapped for c in span):
            missing_groups.append(name)
    return {
        "covered": have, "of": len(LATIN_CORE), "share": round(have / len(LATIN_CORE), 3),
        "complete": have == len(LATIN_CORE), "missing": missing_groups,
    }


# --- the dashboard ---------------------------------------------------------------------------


def tab(artifacts: list[Artifact], kind: str | None = None, board: str | None = None,
        query: str = "") -> list[dict]:
    """the artifacts tab: newest-stable order, filterable by kind, board or name."""
    rows = []
    for artifact in artifacts:
        if kind and artifact.kind != kind:
            continue
        if board and artifact.source.board != board:
            continue
        if query and query.lower() not in artifact.name.lower():
            continue
        row = artifact.as_dict()
        if artifact.kind == "font":
            row["coverage"] = coverage(artifact.meta)
        rows.append(row)
    return sorted(rows, key=lambda row: (row["kind"], row["name"], row["id"]))


def counts(artifacts: list[Artifact]) -> dict:
    """what the tab's filter chips show before you press one."""
    out: dict[str, int] = {}
    for artifact in artifacts:
        out[artifact.kind] = out.get(artifact.kind, 0) + 1
    return dict(sorted(out.items()))


def lineage(artifact: Artifact) -> list[str]:
    """the sentence under an artifact: what made it, so it is never an orphan."""
    src = artifact.source
    line = [f"made on board {src.board}", f"by job {src.job}"]
    if src.preset:
        line.append(f"through {src.preset}")
    if src.variant:
        line.append(f"(variant {src.variant})")
    if artifact.simulated:
        line.append("(simulated: placeholder bytes, no model ran)")
    return [" ".join(line)]
