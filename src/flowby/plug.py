"""plug a gpu: a model server you rent somewhere, reached by flowby over one address.

the owner asked for a plug in the corner of the page that connects "whatever external gpu (vultr,
gcp, amd developer cloud or whatever)" for self-hosting models. the providers have three different
ways to create a machine and no shared api, so this file does not provision anything. what every
one of them gives you is a linux box with a gpu, and what runs on it is a model server. so a plug is
one thing: an ADDRESS that answers like a model server does.

    provider   a label and a how-to-stand-one-up note. it changes no behaviour here.
    endpoint   where the server answers. https, or http to a loopback address through a tunnel.
    token      optional. sent as a bearer token, kept out of everything that is written down.

"connected" means exactly one thing: a health check really got an answer. it is never set by
saying so. a plug that has not been checked is `unchecked`, one that was checked and failed is
`down` with the reason, and the reason is a sentence, not a status code.

what this file will not do, and why:

    - hold a token in anything that is serialised. `as_dict()` has no token field to leak; the
      token lives in `Plug._token` and is read only by `check()`.
    - follow a redirect. a server that redirects a health check to somewhere else is where a token
      goes to the wrong host.
    - talk to a private network address unless the owner said it is a tunnel (see `reachable`).
    - trust the response. only the documented shape counts: vllm documents /health (200 when up)
      and /v1/models (the models served). nothing else is read.

verified against vllm's own docs on 2026-11-09 (docs.vllm.ai/en/latest/serving/online_serving):
/health, /v1/models, /version and /load exist. the --api-key flag and its exact header were NOT on
that page, so the bearer header here is the common convention and is marked as such in `AUTH_NOTE`.
"""

from __future__ import annotations

import ipaddress
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

STATES = ("unchecked", "up", "down")

# the providers, and "other". a note is how to stand a server up there, honestly marked with what
# has and has not been checked. none of it is run by flowby.
#
# `kind` is the one thing that changes behaviour:
#   server   a machine you rent. you run a model server on it (vllm), and flowby asks its /health.
#   hosted   a vendor that runs the model for you behind its own api. there is no machine and no
#            /health to ask, so flowby cannot check it without spending money, and says so.
SERVER, HOSTED = "server", "hosted"

PROVIDERS = {
    "vultr": {
        "kind": SERVER, "label": "Vultr Cloud GPU",
        "note": "create a Cloud GPU instance (NVIDIA; Vultr documents A16 and A100 plans), ssh in, run a vllm server. "
                "Vultr may require some account history before it allows a GPU instance.",
    },
    "gcp": {
        "kind": SERVER, "label": "Google Cloud",
        "note": "create a Compute Engine instance with a GPU attached, ssh in, run a vllm server. "
                "GPU quota has to be granted first and a free-tier account cannot attach one.",
    },
    "azure": {
        "kind": SERVER, "label": "Microsoft Azure",
        "note": "create a virtual machine from an NC or ND GPU series (Azure documents NC A100 v4 and NC H100 v5), "
                "ssh in, run a vllm server. GPU sizes are hidden until you request quota for that series and region.",
    },
    "aws": {
        "kind": SERVER, "label": "Amazon Web Services",
        "note": "launch an EC2 GPU instance (AWS documents P5 with up to 8 H100), ssh in, run a vllm server. "
                "GPU instances count against a vCPU quota that a new account may need to raise first.",
    },
    "amd": {
        "kind": SERVER, "label": "AMD Developer Cloud",
        "note": "create a GPU droplet (MI300X, ROCm image), ssh in, run vllm. AMD's own guide reaches the "
                "port over an ssh tunnel instead of opening it, which is also the safe way here.",
    },
    "nvidia": {
        "kind": SERVER, "label": "NVIDIA GPU, any cloud",
        "note": "any machine with an NVIDIA GPU and CUDA drivers, on any cloud or in your own rack. run a vllm server "
                "and give flowby its address. use this when your provider is not listed.",
    },
    "fal": {
        "kind": HOSTED, "label": "fal.ai",
        "note": "fal runs the model for you. give the endpoint of an app you deployed or a model you call, like "
                "https://queue.fal.run/fal-ai/flux/schnell, and your fal key. fal has no free ping, so flowby does "
                "not check it: the plug stays 'not checked' and the first real run is the proof.",
    },
    "other": {
        "kind": SERVER, "label": "another provider, or your own machine",
        "note": "anything that gives you a gpu and a shell. run a model server and give flowby its address.",
    },
}

HOSTED_UNCHECKED = ("not checked, and flowby will not check it: this vendor has no free ping, so asking would "
                    "spend your money. the first real run is the proof")
# when a hosted run is built, fal's header is 'Authorization: Key <key>' (queue api docs), NOT 'Bearer'.
# nothing sends it yet: a hosted plug is never checked, so _fetch's bearer header is never used for one.
AUTH_NOTE = "sent as 'Authorization: Bearer <token>', the common convention. not confirmed against vllm's --api-key docs."

TIMEOUT = 6.0
MAX_BODY = 256 * 1024     # a health answer is tiny; refuse to read a megabyte of whatever else answers
MAX_MODELS = 64


class PlugRefused(Exception):
    """what was given is not an address flowby will talk to, and the message says why."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # a redirect is refused, not followed
        return None


def parse_endpoint(raw: str, tunnel: bool = False) -> str:
    """the cleaned base url, or PlugRefused. no path, no query, no credentials in the url."""
    text = (raw or "").strip()
    if not text:
        raise PlugRefused("give the address the server answers at, like https://gpu.example.com:8000")
    if "://" not in text:
        raise PlugRefused("start the address with https:// (or http:// through an ssh tunnel to localhost)")
    parts = urllib.parse.urlsplit(text)
    if parts.scheme not in ("http", "https"):
        raise PlugRefused(f"{parts.scheme}:// is not something flowby speaks. use https://")
    if parts.username or parts.password:
        raise PlugRefused("do not put a password in the address. give the token in its own field")
    host = parts.hostname
    if not host:
        raise PlugRefused("that address has no host")
    if parts.query or parts.fragment:
        raise PlugRefused("give the base address only, without a path or query. flowby adds /health itself")
    if parts.path not in ("", "/"):
        raise PlugRefused("give the base address only, without a path. flowby adds /health itself")
    local = _is_loopback(host)
    if parts.scheme == "http" and not local:
        raise PlugRefused("http over the internet sends your token in the clear. use https, or tunnel to localhost over ssh")
    if not local and _is_private(host) and not tunnel:
        raise PlugRefused("that is a private network address. if it is reached through a tunnel you set up, say so; otherwise use the public https address")
    try:
        port = parts.port
    except ValueError:
        raise PlugRefused("that port is not a number between 1 and 65535") from None
    netloc = f"[{host}]" if ":" in host else host
    return f"{parts.scheme}://{netloc}" + (f":{port}" if port else "")


# the one host each hosted vendor answers at. an address for a hosted plug must be on it, so a typo or a
# lookalike can never receive the key. the host is from fal's queue api docs (queue.fal.run).
HOSTED_HOSTS = {"fal": ("queue.fal.run",)}


def parse_hosted(provider: str, raw: str) -> str:
    """the cleaned address of a hosted app: https, the vendor's own host, an owner/app path, nothing else."""
    text = (raw or "").strip()
    if not text:
        raise PlugRefused("give the endpoint, like https://queue.fal.run/fal-ai/flux/schnell")
    parts = urllib.parse.urlsplit(text)
    if parts.scheme != "https":
        raise PlugRefused("a hosted endpoint is https only, because your key goes with it")
    if parts.username or parts.password:
        raise PlugRefused("do not put a password in the address. give the key in its own field")
    if parts.query or parts.fragment:
        raise PlugRefused("give the endpoint without a query")
    allowed = HOSTED_HOSTS.get(provider, ())
    if (parts.hostname or "").lower() not in allowed:
        raise PlugRefused(f"a {PROVIDERS[provider]['label']} endpoint lives at {allowed[0]}. that is the only host the key is sent to")
    try:
        parts.port
    except ValueError:
        raise PlugRefused("that port is not a number between 1 and 65535") from None
    if parts.port not in (None, 443):
        raise PlugRefused(f"{allowed[0]} answers on the standard https port only")
    segments = [seg for seg in parts.path.split("/") if seg]
    if len(segments) < 2:
        raise PlugRefused("add the owner and app after the host, like /fal-ai/flux/schnell")
    if any(seg in (".", "..") for seg in segments):
        raise PlugRefused("that path has a . or .. in it")
    return f"https://{allowed[0]}/" + "/".join(segments)


def _is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def resolves_public(host: str, tunnel: bool, resolver=socket.getaddrinfo) -> str | None:
    """None if the host is fine to talk to, otherwise the sentence for why not.

    parse_endpoint can only judge a literal address. a NAME is as public as what it resolves to, and
    a name an attacker controls can resolve to 10.0.0.5 or 127.0.0.1. so the name is resolved here,
    right before a request, and every address it gives must be public, or the owner said tunnel.
    a loopback host is allowed without saying so because that is what an ssh tunnel looks like.
    """
    if _is_loopback(host):
        return None
    try:
        found = resolver(host, None)
    except (socket.gaierror, UnicodeError, OSError):
        return "that address does not resolve. check for a typo"
    addresses = {item[4][0] for item in found}
    if not addresses:
        return "that address does not resolve. check for a typo"
    for text in addresses:
        try:
            ip = ipaddress.ip_address(text.split("%")[0])
        except ValueError:
            return "that address resolved to something that is not an ip address"
        if ip.is_loopback:
            continue    # a name that points at this machine is a tunnel too
        if (not ip.is_global or ip.is_multicast) and not tunnel:
            return f"{host} resolves to a private address ({text}). if that is a tunnel you set up, say so; otherwise use the public address"
    return None


def _is_private(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False       # a hostname: resolved at check time, and checked again there
    # not globally routable is the whole rule: it covers private, link-local (169.254.169.254 is the
    # cloud metadata address), reserved, multicast and unspecified in one test, and it is stricter
    # than listing them, because a new reserved range is refused without anyone adding it.
    # python calls multicast "global", and no model server lives at a multicast address
    return not ip.is_global or ip.is_multicast


@dataclass
class Plug:
    id: str
    label: str
    provider: str
    endpoint: str
    state: str = "unchecked"
    detail: str = "not checked yet"
    models: list = field(default_factory=list)
    version: str | None = None
    checked_at: float | None = None
    latency_ms: int | None = None
    tunnel: bool = False
    _token: str = field(default="", repr=False, compare=False)

    def as_dict(self) -> dict:
        """everything a page may see. there is deliberately no token here, not even masked: a
        masked token still says how long it is and how it starts."""
        return {
            "id": self.id, "label": self.label, "provider": self.provider,
            "provider_label": PROVIDERS[self.provider]["label"], "kind": PROVIDERS[self.provider]["kind"], "endpoint": self.endpoint,
            "state": self.state, "detail": self.detail, "models": list(self.models), "version": self.version,
            "checked_at": self.checked_at, "latency_ms": self.latency_ms, "tunnel": self.tunnel,
            "has_token": bool(self._token),
        }

    def __repr__(self) -> str:
        return f"Plug({self.id!r}, {self.endpoint!r}, {self.state!r})"


def make(plug_id: str, label: str, provider: str, endpoint: str, token: str = "", tunnel: bool = False) -> Plug:
    if provider not in PROVIDERS:
        raise PlugRefused(f"{provider!r} is not a provider flowby knows. the choices are {', '.join(PROVIDERS)}")
    clean = (label or "").strip()
    if not clean:
        raise PlugRefused("give the plug a name, so you can tell it from the next one")
    if any(ch in (token or "") for ch in "\r\n\x00"):
        raise PlugRefused("a token cannot contain a line break")
    if PROVIDERS[provider]["kind"] == HOSTED:
        if tunnel:
            raise PlugRefused("a hosted vendor is reached over the internet, so there is no tunnel to speak of")
        url = parse_hosted(provider, endpoint)
    else:
        url = parse_endpoint(endpoint, tunnel=tunnel)
    made = Plug(id=plug_id, label=clean[:60], provider=provider, endpoint=url, tunnel=bool(tunnel), _token=(token or "").strip())
    if PROVIDERS[provider]["kind"] == HOSTED:
        made.detail = HOSTED_UNCHECKED
    return made


def _fetch(plug: Plug, path: str, opener, timeout: float):
    request = urllib.request.Request(plug.endpoint + path, headers={"Accept": "application/json", "User-Agent": "flowby"})
    if plug._token:
        request.add_header("Authorization", f"Bearer {plug._token}")
    with opener.open(request, timeout=timeout) as response:
        body = response.read(MAX_BODY + 1)
        if len(body) > MAX_BODY:
            raise PlugRefused("the server answered with far more than a health check should")
        return response.status, body


def check(plug: Plug, opener=None, clock=time.time, timeout: float = TIMEOUT, resolver=socket.getaddrinfo) -> Plug:
    """really ask the server. the only function here that touches the network, and the only one
    that can make a plug `up`. `opener` is injectable so the tests can stand a server up."""
    if PROVIDERS[plug.provider]["kind"] == HOSTED:
        # nothing is sent. fal documents no free ping; the only documented call is a billable run, and a
        # check that spends money without being asked is worse than a plug that says it is unchecked.
        plug.checked_at, plug.models, plug.version, plug.latency_ms = None, [], None, None
        plug.state = "unchecked"
        plug.detail = HOSTED_UNCHECKED
        return plug
    opener = opener or urllib.request.build_opener(_NoRedirect)
    started = clock()
    plug.checked_at = started
    plug.models, plug.version, plug.latency_ms = [], None, None
    # resolve and judge the name BEFORE a byte or a token is sent anywhere
    host = urllib.parse.urlsplit(plug.endpoint).hostname or ""
    refusal = resolves_public(host, plug.tunnel, resolver)
    if refusal:
        return _down(plug, refusal)
    try:
        status, _ = _fetch(plug, "/health", opener, timeout)
    except urllib.error.HTTPError as problem:
        return _down(plug, _http_words(problem.code, bool(plug._token)))
    except PlugRefused as problem:
        return _down(plug, str(problem))
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as problem:
        return _down(plug, _net_words(problem))
    if status != 200:
        return _down(plug, f"the server answered {status} to /health, and a healthy one answers 200")
    plug.latency_ms = max(0, int((clock() - started) * 1000))

    # the models are a second question: a server can be up and serving nothing yet while it loads
    try:
        code, raw = _fetch(plug, "/v1/models", opener, timeout)
        data = json.loads(raw or b"{}")
        rows = data.get("data") if isinstance(data, dict) else None
        if code == 200 and isinstance(rows, list):
            plug.models = [str(r["id"])[:120] for r in rows[:MAX_MODELS] if isinstance(r, dict) and "id" in r]
    except (urllib.error.URLError, OSError, ValueError, PlugRefused):
        plug.models = []   # health passed; the model list did not. up, with nothing to list
    try:
        code, raw = _fetch(plug, "/version", opener, timeout)
        data = json.loads(raw or b"{}")
        if code == 200 and isinstance(data, dict) and isinstance(data.get("version"), str):
            plug.version = data["version"][:40]
    except (urllib.error.URLError, OSError, ValueError, PlugRefused):
        plug.version = None

    plug.state = "up"
    plug.detail = (f"answered in {plug.latency_ms} ms, serving {', '.join(plug.models[:3])}"
                   + (f" and {len(plug.models) - 3} more" if len(plug.models) > 3 else "")) if plug.models \
        else f"answered in {plug.latency_ms} ms, and is not serving a model yet"
    return plug


def _scrub(text: str, token: str) -> str:
    """the token, removed from any sentence about to be shown. the sentences here are written not to
    contain it, and this is the second wall in case a library's message ever does."""
    if token and token in text:
        text = text.replace(token, "[token]")
    return text


def _down(plug: Plug, why: str) -> Plug:
    plug.state, plug.detail = "down", _scrub(why, plug._token)
    return plug


def _http_words(code: int, had_token: bool) -> str:
    if code in (401, 403):
        return ("the server refused the token" if had_token else "the server wants a token and none was given")
    if code == 404:
        return "the server answered, but not like a model server: there is no /health. check the port and that it is vllm"
    if code in (301, 302, 303, 307, 308):
        return "the server redirected the health check, and flowby does not follow redirects with a token"
    if code >= 500:
        return f"the server is up but unwell (it answered {code}). it may still be loading the model"
    return f"the server answered {code} to /health"


def _net_words(problem: Exception) -> str:
    reason = getattr(problem, "reason", problem)
    if isinstance(reason, (socket.timeout, TimeoutError)):
        return "nothing answered in time. the machine may be off, the port closed by a firewall, or still booting"
    if isinstance(reason, ConnectionRefusedError):
        return "the machine is there and nothing is listening on that port. the model server is not running"
    text = str(reason).lower()
    if "name or service not known" in text or "nodename nor servname" in text or "getaddrinfo" in text:
        return "that address does not resolve. check for a typo"
    if "certificate" in text or "ssl" in text:
        return "the https certificate could not be verified. flowby does not skip that check"
    # never the library's own words: an exception message can echo a header, and a header holds the token
    return f"could not reach it ({type(reason).__name__})"


class Plugs:
    """the plugs a person has made. a token goes in with `add` and never comes out."""

    def __init__(self):
        self._plugs: dict[str, Plug] = {}
        self._serial = 0

    def add(self, label: str, provider: str, endpoint: str, token: str = "", tunnel: bool = False) -> Plug:
        self._serial += 1
        plug = make(f"plug-{self._serial}", label, provider, endpoint, token, tunnel)
        for other in self._plugs.values():
            if other.endpoint == plug.endpoint:
                raise PlugRefused(f"{other.label!r} is already plugged in at {plug.endpoint}")
        self._plugs[plug.id] = plug
        return plug

    def get(self, plug_id: str) -> Plug:
        try:
            return self._plugs[plug_id]
        except KeyError:
            raise PlugRefused(f"{plug_id!r} is not a plug") from None

    def remove(self, plug_id: str) -> None:
        self.get(plug_id)
        del self._plugs[plug_id]

    def all(self) -> list[dict]:
        return [p.as_dict() for p in self._plugs.values()]

    def serving(self, model: str) -> list[Plug]:
        """the plugs that are up and say they serve this model. nothing else counts as a place to run it."""
        return [p for p in self._plugs.values() if p.state == "up" and model in p.models]
