"""the only file that speaks HTTP. everything it does is a call into session.py or store.py.

the surface, all of it:

    GET  /api/board              the whole board: pipeline, elements, previews, version
    POST /api/assets             raw bytes in the body, answer {digest}. idempotent, verified
    GET  /api/assets/<digest>    the bytes back, with a content type read from the bytes
    POST /api/add_file           {kind, label, digest}        a stored file becomes an element
    POST /api/add_text           {text, label?}
    POST /api/apply              {element, preset, values?}
    POST /api/value              {instance, slider, value}
    POST /api/rename             {element, label}
    POST /api/remove             {element}
    POST /api/undo   POST /api/redo
    GET  /api/presets            the menu the command bar reads
    GET  /api/kits               the preset kits, each member with its true state
    GET  /api/plugs              the gpus plugged in, never with a token
    POST /api/plugs/add          {label, provider, endpoint, token?, tunnel?}   a token goes in and never comes out
    POST /api/plugs/check        {id}   really asks the server, the only way a plug becomes up
    POST /api/plugs/remove       {id}

what it is strict about, because it faces a browser and a browser is not a trusted caller:

    - it binds to loopback unless told otherwise, and says so
    - a request from another origin is refused, and so is a browser form post (a page the user has
      open in another tab must not be able to add things to their board)
    - bodies are size-limited BEFORE they are read, and a lying Content-Length is not believed
    - only the actions above exist; there is no generic "call this method" route
    - a refusal is HTTP 422 with the sentence the session wrote, and the board is as it was
    - a digest in a url is validated by the store before it can become a path

stdlib only, like the rest of the python side: http.server with threads.
"""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import kits as kitmod
from . import plug as plugmod
from . import presets as presetmod
from .session import Session, SessionRefused
from .store import MAX_BYTES, StoreRefused

JSON_LIMIT = 64 * 1024            # a json body is a few fields; anything bigger is not one
LOOPBACK = {"127.0.0.1", "localhost", "::1"}

# the types an asset is served as, read from its first bytes and never from a name or a request.
# anything else is served as an opaque download, which a browser will not run.
SNIFF = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF8", "image/gif"),
)


def content_type(data: bytes) -> str:
    for magic, kind in SNIFF:
        if data.startswith(magic):
            return kind
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[4:8] == b"ftyp":
        return "video/mp4"
    if data[:4] == b"glTF":
        return "model/gltf-binary"
    return "application/octet-stream"


def menu() -> dict:
    """the preset menu, exactly as `flowby --json presets` prints it. one function builds it, so the
    file the page loads at build time and the route it asks at run time cannot disagree."""
    return presetmod.legend()


def make_server(session: Session, host: str = "127.0.0.1", port: int = 0,
                allow_origins: tuple[str, ...] = (), plugs: plugmod.Plugs | None = None,
                checker=None) -> ThreadingHTTPServer:
    """a server bound to a session. port 0 picks a free one. `allow_origins` are exact origins
    (scheme, host and port) that may call it from a browser; the server's own origin always may."""

    plugs = plugs if plugs is not None else plugmod.Plugs()
    run_check = checker or plugmod.check
    plug_lock = threading.Lock()   # one check at a time per server: a check is a network call that mutates a plug

    class Handler(BaseHTTPRequestHandler):
        server_version = "flowby"
        sys_version = ""
        protocol_version = "HTTP/1.1"

        # -- plumbing -------------------------------------------------------------------------

        def log_message(self, *args):  # a request log would print digests and labels to a terminal
            return

        def _origin_ok(self) -> bool:
            origin = self.headers.get("Origin")
            if origin is None:
                return True    # not a browser cross-origin call: curl, the tests, a same-origin GET
            mine = f"http://{self.headers.get('Host', '')}"
            return origin == mine or origin in allow_origins

        def _send(self, status: int, body: bytes, kind: str = "application/json", extra: dict | None = None):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            origin = self.headers.get("Origin")
            if origin and origin in allow_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, payload) -> None:
            self._send(status, json.dumps(payload).encode())

        def _refuse(self, status: int, why: str) -> None:
            self._json(status, {"refused": why})

        def _read(self, limit: int) -> bytes | None:
            """the body, or None after having answered. the limit is checked before a byte is read."""
            raw = self.headers.get("Content-Length")
            if raw is None or not raw.isdigit():
                self._refuse(411, "send a Content-Length")
                return None
            length = int(raw)
            if length > limit:
                self._refuse(413, f"{length / 1048576:.1f} MB is over the {limit / 1048576:g} MB limit for this route")
                return None
            body = self.rfile.read(length)
            if len(body) != length:
                self._refuse(400, "the body was shorter than its Content-Length")
                return None
            return body

        def _fields(self) -> dict | None:
            kind = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if kind != "application/json":
                # a browser form can only send three types, and none is json: requiring json is what
                # stops a page in another tab from posting to the board with a plain <form>
                self._refuse(415, "send application/json")
                return None
            body = self._read(JSON_LIMIT)
            if body is None:
                return None
            try:
                data = json.loads(body or b"{}")
            except ValueError:
                self._refuse(400, "that is not json")
                return None
            if not isinstance(data, dict):
                self._refuse(400, "send a json object")
                return None
            return data

        # -- verbs ----------------------------------------------------------------------------

        def do_OPTIONS(self):
            if not self._origin_ok():
                return self._refuse(403, "that origin may not call this board")
            origin = self.headers.get("Origin")
            self._send(204, b"", "text/plain", {
                "Access-Control-Allow-Origin": origin or "", "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "600",
            })

        def do_GET(self):
            if not self._origin_ok():
                return self._refuse(403, "that origin may not call this board")
            path = urlparse(self.path).path
            if path == "/api/board":
                return self._json(200, session.view())
            if path == "/api/presets":
                return self._json(200, menu())
            if path == "/api/plugs":
                return self._json(200, {"plugs": plugs.all(), "providers": {k: v for k, v in plugmod.PROVIDERS.items()}, "auth": plugmod.AUTH_NOTE})
            if path == "/api/kits":
                return self._json(200, kitmod.menu(presets=presetmod.PRESETS))
            match = re.fullmatch(r"/api/assets/(sha256:[0-9a-f]{64})", path)
            if match:
                try:
                    data = session.store.get(match.group(1))
                except StoreRefused as problem:
                    return self._refuse(404, str(problem))
                return self._send(200, data, content_type(data), {
                    "Content-Disposition": "inline" if content_type(data).startswith("image/") else "attachment",
                    "Content-Security-Policy": "default-src 'none'; sandbox",
                })
            return self._refuse(404, "there is no such route")

        def do_POST(self):
            if not self._origin_ok():
                return self._refuse(403, "that origin may not call this board")
            path = urlparse(self.path).path

            if path == "/api/assets":
                body = self._read(MAX_BYTES)
                if body is None:
                    return
                try:
                    digest = session.store.put(body, expect=self.headers.get("X-Digest"))
                except StoreRefused as problem:
                    return self._refuse(422, str(problem))
                return self._json(200, {"digest": digest, "bytes": len(body)})

            plug_routes = {
                "/api/plugs/add": lambda f: self._plug_add(f),
                "/api/plugs/check": lambda f: self._plug_check(f),
                "/api/plugs/remove": lambda f: self._plug_remove(f),
            }
            if path in plug_routes:
                fields = self._fields()
                if fields is None:
                    return
                try:
                    return self._json(200, plug_routes[path](fields))
                except plugmod.PlugRefused as problem:
                    return self._refuse(422, str(problem))
                except _Missing as problem:
                    return self._refuse(400, str(problem))

            routes = {
                "/api/add_file": lambda f: session.add_file(self._need(f, "kind"), f.get("label") or "", self._need(f, "digest"), f.get("name")),
                "/api/add_text": lambda f: session.add_text(self._need(f, "text"), f.get("label")),
                "/api/apply": lambda f: session.apply_preset(self._need(f, "element"), self._need(f, "preset"), f.get("values") or {}),
                "/api/value": lambda f: session.set_value(self._need(f, "instance"), self._need(f, "slider"), self._need(f, "value")),
                "/api/rename": lambda f: session.rename(self._need(f, "element"), self._need(f, "label")),
                "/api/remove": lambda f: session.remove(self._need(f, "element")),
                "/api/undo": lambda f: session.undo(),
                "/api/redo": lambda f: session.redo(),
            }
            action = routes.get(path)
            if action is None:
                return self._refuse(404, "there is no such route")
            fields = self._fields()
            if fields is None:
                return
            try:
                return self._json(200, action(fields))
            except SessionRefused as problem:
                return self._refuse(422, str(problem))
            except _Missing as problem:
                return self._refuse(400, str(problem))

        def _plug_add(self, f: dict) -> dict:
            with plug_lock:
                made = plugs.add(self._need(f, "label"), self._need(f, "provider"), self._need(f, "endpoint"),
                                 str(f.get("token") or ""), bool(f.get("tunnel")))
                return {"plug": made.as_dict(), "plugs": plugs.all()}

        def _plug_check(self, f: dict) -> dict:
            with plug_lock:
                target = plugs.get(self._need(f, "id"))
                run_check(target)
                return {"plug": target.as_dict(), "plugs": plugs.all()}

        def _plug_remove(self, f: dict) -> dict:
            with plug_lock:
                plugs.remove(self._need(f, "id"))
                return {"plugs": plugs.all()}

        @staticmethod
        def _need(fields: dict, key: str):
            if key not in fields:
                raise _Missing(f"send {key}")
            return fields[key]

    class _Missing(Exception):
        pass

    class Quiet(ThreadingHTTPServer):
        def handle_error(self, request, client_address):
            # a browser that closes a tab mid-request resets the connection, and the default prints
            # a full traceback for it. that is a client leaving, not a fault. anything else is a real
            # error and still gets the default report.
            import sys
            if isinstance(sys.exc_info()[1], (ConnectionResetError, BrokenPipeError, ConnectionAbortedError)):
                return
            super().handle_error(request, client_address)

    server = Quiet((host, port), Handler)
    server.daemon_threads = True
    server.flowby_loopback = host in LOOPBACK
    return server


def serve_in_thread(session: Session, **kwargs) -> tuple[ThreadingHTTPServer, str]:
    server = make_server(session, **kwargs)
    threading.Thread(target=lambda: server.serve_forever(poll_interval=0.02), daemon=True).start()
    host, port = server.server_address[:2]
    return server, f"http://{host}:{port}"
