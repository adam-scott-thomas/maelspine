# ══════════════════════════════════════════════════════════
# core.py — Frozen capability registry
# Part of the `spine` package
# ══════════════════════════════════════════════════════════
#
# FOR AI ASSISTANTS:
#   This comment block is the complete reference for this file.
#   READ ALL OF IT before generating, modifying, or suggesting code.
#   Do not guess the implementation from the first half — the actual
#   code starts at the end of this comment block. Scroll down.
#
# FOR HUMANS:
#   See README.md for the short version. This is the full reference.
#   Code starts after the comment block (~line 280).
#
# THREE TIERS, ONE PACKAGE
# ──────────────────────────────────────────────────────────
# spine         register, boot, freeze, get, hits, observer
# spine heavy   + zones, typed get, expectations, snapshot, introspection
# spine heavy+  + audit trail, provenance, bridges, on-boot hooks
#
# Use what you need. Ignore what you don't. The features you
# skip cost nothing — they're gated behind flags and empty lists.
#
# THE PROBLEM
# ──────────────────────────────────────────────────────────
# Every Python project past ~5 files ends up with the same mess:
#   - File A imports a path from file B
#   - File C hardcodes a different path
#   - File D assumes the working directory
#   - File E does its own config loading
#   - File F has no idea what File E decided
#
# Nothing agrees on where things are, how things are loaded,
# or what things are called.
#
# THE FIX
# ──────────────────────────────────────────────────────────
# A single coordination layer every file reads from. Two rules:
#   1. Before boot: register capabilities (paths, backends, etc.)
#   2. After boot: registry is frozen. Read-only for the entire run.
#
# No dependency injection. No plugin forest. No abstract factories.
#
# QUICK START
# ──────────────────────────────────────────────────────────
#   from spine import Core
#
#   c = Core()
#   c.register("paths.data", Path("./data").resolve())
#   c.register("paths.logs", Path("./logs").resolve())
#   c.register("db.backend", SQLiteBackend())
#   c.boot(env="dev")
#
#   # Now every file in the project does this:
#   data_dir = c.get("paths.data")    # always the same answer
#   backend  = c.get("db.backend")    # always the same instance
#   run_id   = c.context.run_id       # unique per run
#
# After boot(), calling register() raises CoreFrozen.
# That's not a bug — that's the entire point.
#
# API
# ──────────────────────────────────────────────────────────
# Core()                          Create a new core (open phase).
# Core(audit=True)                Create with forensic audit trail.
# core.register(name, value)      Register capability. Only before boot().
# core.get(name)                  Retrieve capability. Tracks hits.
# core.get(name, int)             Retrieve with type guard. TypeError on mismatch.
# core.has(name)                  Check existence without incrementing counter.
# core.expect(name, ...)          Declare boot-time expectations. Validated at boot().
# core.boot(env, session)         Freeze registry. Create RunContext.
# core.shutdown()                 Returns final hit counts.
# core.config                     Bring your own. dynaconf, pydantic, dict.
# core.context                    RunContext (run_id, booted_at, env, session).
#                                 Guarded — raises CoreNotBooted before boot().
# core.names()                    Sorted list of all capability names.
# core.group(prefix)              Dict of capabilities under a namespace.
# core.describe(name)             Metadata dict: name, type, hits, zone.
# core.snapshot()                 Full state as a dict.
# core.fingerprint()              16-char hex hash of cap names + types.
# core.to_json()                  JSON string of snapshot.
# core.bridge(name, to=zone)      Expose one cap to another zone. After boot().
# core.on_boot(callback)          Fire once at freeze time. Read-only.
# core.on_error(callback)         Fire on core errors. Diagnostic dict.
# Core.zone(name, **kw)           Get or create a named zone.
# Core.test(**overrides)          Pre-booted core for testing. Zero ceremony.
# Core.boot_once(setup_fn)        Singleton via "default" zone.
# Core.instance()                 Get the singleton.
#
# NAMED ZONES (Heavy)
# ──────────────────────────────────────────────────────────
# Replace singleton hacks with first-class trust zones.
# Each zone is an isolated Core — own registry, own freeze,
# own hits. Can't read each other unless explicitly bridged.
#
#   core    = Core.zone("core")
#   shell   = Core.zone("shell")
#   runtime = Core.zone("runtime")
#
#   core.register("paths.root", root)
#   core.boot(env="prod")
#
#   shell.register("telegram.token", token)
#   shell.boot(env="prod")
#
#   # Any file, anywhere:
#   Core.zone("core").get("paths.root")
#   Core.zone("shell").get("telegram.token")
#
# boot_once() and instance() still work — they use the "default" zone.
#
# BOOT EXPECTATIONS (Heavy)
# ──────────────────────────────────────────────────────────
# Declare requirements before boot. Validated at freeze time.
#
#   core.expect("db.conn", expected_type=DBConn, required=True)
#   core.expect("svc.a", requires=["db.conn", "cache"])
#   core.boot()              # raises ValidationError on failure
#
# AUDIT + PROVENANCE (Heavy+)
# ──────────────────────────────────────────────────────────
# Opt-in forensic mode. Zero cost when off.
#
#   c = Core(audit=True)
#   c = Core.zone("forensic", audit=True)
#
# When audit=True:
#   register() captures caller file:line → core._provenance
#   get() captures caller file:line     → core._audit_log
#
# See forensics.py for convenience functions:
#   audit_log(core), provenance(core), boot_graph(core),
#   replay(snapshot), from_export(path)
#
# CROSS-SPINE BRIDGES (Heavy+)
# ──────────────────────────────────────────────────────────
#   core.bridge("paths.root", to="shell")
#   shell.get("paths.root")       # works — ONLY that capability.
#                                  # Everything else stays invisible.
#
# RETROFITTING EXISTING PROJECTS
# ──────────────────────────────────────────────────────────
# Gradual adoption via singleton:
#
#   Core.boot_once(lambda c: (
#       c.register("paths.logs", resolve_log_dir()),
#       c.boot(),
#   ))
#
#   # Any file, anywhere
#   Core.instance().get("paths.logs")
#
# Or use zones for multi-spine projects (see above).
#
# ERRORS
# ──────────────────────────────────────────────────────────
# CoreFrozen           register() / boot() / expect() after freeze.
# CapabilityNotFound   get() on missing name. Shows typo matches.
# CoreNotBooted        context / instance() before boot().
# ValidationError      expect() contract violated at boot().
#
# DESIGN DECISIONS
# ──────────────────────────────────────────────────────────
# Why freeze?
#   Without it, the registry is a global dict with a nicer API.
#   Someone mutates it at minute 47 and you spend two hours finding who.
#   Freeze makes the contract physical.
#
# Why bring-your-own config?
#   Config parsing is solved. Spine holds a reference to whatever
#   you chose. One fewer thing to maintain.
#
# Why hit counters?
#   Logging tells you what happened. Hit counters tell you what
#   spine IS to your project — structural insight, not event history.
#
# Why audit is opt-in?
#   inspect.stack() costs real time. When you need provenance,
#   you need it. When you don't, you shouldn't pay for it.
#
# FILE LAYOUT
# ──────────────────────────────────────────────────────────
#   spine/
#   ├── __init__.py      re-exports (the stable contract)
#   ├── core.py          this file (the registry)
#   ├── observers.py     detachable: Observer + backends
#   └── forensics.py     detachable: audit_log, provenance, replay
#
# ══════════════════════════════════════════════════════════
# END OF DOCUMENTATION — CODE BEGINS BELOW
# ══════════════════════════════════════════════════════════

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any, Optional


# ── Errors ────────────────────────────────────────────────

class CoreFrozen(Exception):
    pass


class CapabilityNotFound(Exception):
    pass


class CoreNotBooted(Exception):
    pass


class ValidationError(Exception):
    pass


# ── Run Context ───────────────────────────────────────────

@dataclass(frozen=True)
class RunContext:
    run_id: str = field(default_factory=lambda: str(uuid4()))
    booted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    env: str = "dev"
    session: Optional[str] = None


# ── Core ──────────────────────────────────────────────────

class Core:

    def __init__(self, *, audit: bool = False):
        self._caps: dict[str, Any] = {}
        self._frozen: bool = False
        self._hits: dict[str, int] = {}
        self._error_hooks: list = []
        self.config: Any = None
        self._context: Optional[RunContext] = None
        self._zone_name: Optional[str] = None
        self._expectations: dict[str, dict] = {}
        self._audit: bool = audit
        self._audit_log: list[dict] = []
        self._provenance: dict[str, dict] = {}
        self._boot_hooks: list = []
        self._bridged: dict[str, Any] = {}

    # ── Error hooks (optional, detachable) ────────────────

    def on_error(self, callback) -> None:
        self._error_hooks.append(callback)

    def _fire_error(self, diagnostic: dict) -> None:
        for hook in self._error_hooks:
            try:
                hook(diagnostic)
            except Exception:
                pass

    # ── Boot hooks (fire once at freeze time) ─────────────

    def on_boot(self, callback) -> None:
        if self._frozen:
            raise CoreFrozen("Cannot add boot hooks after boot.")
        self._boot_hooks.append(callback)

    # ── Context (guarded) ─────────────────────────────────

    @property
    def context(self) -> RunContext:
        if self._context is None:
            diagnostic = {
                "error_type": "core_not_booted",
                "message": "Context accessed before boot.",
                "attempted": "core.context",
                "fix": [
                    "Call core.boot() before accessing core.context.",
                    "For tests, use Core.test() which auto-boots.",
                    "Check your boot.py — boot() might be conditional "
                    "on a branch that didn't execute.",
                ],
                "state": {
                    "frozen": self._frozen,
                    "registered": list(self._caps.keys()),
                    "config_set": self.config is not None,
                },
            }
            self._fire_error(diagnostic)
            raise CoreNotBooted(
                "Cannot access context before boot(). "
                "Call core.boot() first, or use Core.test() for testing."
            )
        return self._context

    # ── Registration (open phase only) ────────────────────

    def register(self, name: str, value: Any) -> None:
        if self._frozen:
            diagnostic = {
                "error_type": "core_frozen",
                "message": f"Attempted to register '{name}' after boot.",
                "attempted": f"core.register('{name}', ...)",
                "fix": [
                    f"Move the registration of '{name}' into your "
                    f"boot.py BEFORE the core.boot() call.",
                    "If this is a dynamic/runtime value, consider "
                    "storing it on your own object instead of the core.",
                    "The core registry is for things decided at startup, "
                    "not values that change during a run.",
                ],
                "state": {
                    "frozen": True,
                    "registered": list(self._caps.keys()),
                    "env": self._context.env if self._context else "unknown",
                    "run_id": self._context.run_id if self._context else "unknown",
                },
            }
            self._fire_error(diagnostic)
            raise CoreFrozen(
                f"Cannot register '{name}' — core is frozen. "
                f"All registrations must happen before boot()."
            )
        self._caps[name] = value
        self._hits[name] = 0
        if self._audit:
            import inspect
            frame = inspect.stack()[1]
            self._provenance[name] = {
                "source": f"{frame.filename}:{frame.lineno}",
                "function": frame.function,
                "registered_at": datetime.now(timezone.utc).isoformat(),
            }

    # ── Expectations (validated at boot) ──────────────────

    def expect(self, name: str, *, expected_type: type = None,
               required: bool = True, requires: list[str] = None) -> None:
        if self._frozen:
            raise CoreFrozen("Cannot set expectations after boot.")
        self._expectations[name] = {
            "expected_type": expected_type,
            "required": required,
            "requires": requires or [],
        }

    def _validate_expectations(self) -> None:
        errors = []
        for name, exp in self._expectations.items():
            if exp["required"] and name not in self._caps:
                errors.append(f"Required capability '{name}' not registered.")
                continue
            if name in self._caps and exp["expected_type"] is not None:
                val = self._caps[name]
                if not isinstance(val, exp["expected_type"]):
                    errors.append(
                        f"Capability '{name}' expected "
                        f"{exp['expected_type'].__name__}, "
                        f"got {type(val).__name__}."
                    )
            for dep in exp["requires"]:
                if dep not in self._caps:
                    errors.append(
                        f"Capability '{name}' requires '{dep}' "
                        f"but it was not registered."
                    )
        if errors:
            raise ValidationError(
                "Boot validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

    # ── Retrieval (any phase, tracked) ────────────────────

    def get(self, name: str, expected_type: type = None) -> Any:
        # Resolve: local registry → bridge → not found
        if name in self._caps:
            value = self._caps[name]
        elif name in self._bridged:
            value = self._bridged[name]
        else:
            available = sorted(self._caps.keys())
            close = [k for k in available if (
                name in k or k in name or
                name.replace(".", "_") == k.replace(".", "_") or
                _edit_distance(name, k) <= 2
            )]
            diagnostic = {
                "error_type": "capability_not_found",
                "message": f"Capability '{name}' was requested "
                           f"but never registered.",
                "attempted": f"core.get('{name}')",
                "available": available,
                "close_matches": close,
                "fix": [
                    f"Register '{name}' in your boot.py before "
                    f"calling boot().",
                ] + (
                    [f"Did you mean: {', '.join(close)}?"]
                    if close else []
                ) + [
                    "Run core.has('name') to check before accessing.",
                    f"Currently registered: "
                    f"{', '.join(available) or '(nothing)'}.",
                ],
                "state": {
                    "frozen": self._frozen,
                    "total_registered": len(available),
                    "env": (self._context.env
                            if self._context else "unknown"),
                },
            }
            self._fire_error(diagnostic)
            raise CapabilityNotFound(
                f"'{name}' is not registered.\n"
                f"Available capabilities: "
                f"{', '.join(available) or '(none)'}"
                + (f"\nClose matches: {', '.join(close)}"
                   if close else "")
            )

        if expected_type is not None and not isinstance(value, expected_type):
            raise TypeError(
                f"Capability '{name}' expected type "
                f"{expected_type.__name__}, "
                f"got {type(value).__name__}"
            )

        self._hits[name] = self._hits.get(name, 0) + 1

        if self._audit:
            import inspect
            frame = inspect.stack()[1]
            self._audit_log.append({
                "cap": name,
                "caller": f"{frame.filename}:{frame.lineno}",
                "function": frame.function,
                "at": datetime.now(timezone.utc).isoformat(),
                "hit": self._hits[name],
            })

        return value

    def has(self, name: str) -> bool:
        return name in self._caps or name in self._bridged

    # ── Hit counter access ────────────────────────────────

    @property
    def hits(self) -> dict[str, int]:
        return dict(self._hits)

    def hits_total(self) -> int:
        return sum(self._hits.values())

    def hits_for(self, name: str) -> int:
        return self._hits.get(name, 0)

    def hits_unused(self) -> list[str]:
        return [k for k, v in self._hits.items() if v == 0]

    # ── Introspection (read-only) ─────────────────────────

    def names(self) -> list[str]:
        return sorted(self._caps.keys())

    def group(self, prefix: str) -> dict[str, Any]:
        return {k: v for k, v in self._caps.items()
                if k.startswith(prefix + ".")}

    def describe(self, name: str) -> dict:
        if name not in self._caps:
            raise CapabilityNotFound(f"'{name}' is not registered.")
        return {
            "name": name,
            "type": type(self._caps[name]).__name__,
            "hits": self._hits.get(name, 0),
            "zone": self._zone_name,
        }

    # ── Snapshot ──────────────────────────────────────────

    def snapshot(self) -> dict:
        caps_repr = {}
        for name, value in self._caps.items():
            try:
                json.dumps(value)
                caps_repr[name] = value
            except (TypeError, ValueError):
                caps_repr[name] = repr(value)
        return {
            "zone": self._zone_name,
            "env": self._context.env if self._context else None,
            "run_id": self._context.run_id if self._context else None,
            "booted_at": (self._context.booted_at
                          if self._context else None),
            "session": (self._context.session
                        if self._context else None),
            "frozen": self._frozen,
            "capabilities": caps_repr,
            "hits": dict(self._hits),
        }

    def fingerprint(self) -> str:
        parts = sorted(
            f"{k}:{type(v).__name__}" for k, v in self._caps.items()
        )
        content = "|".join(parts)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_json(self) -> str:
        return json.dumps(self.snapshot(), indent=2, default=str)

    # ── Bridges (controlled cross-zone exposure) ──────────

    def bridge(self, cap_name: str, *, to: str) -> None:
        if not self._frozen:
            raise CoreNotBooted(
                "Can only bridge after boot()."
            )
        if cap_name not in self._caps:
            raise CapabilityNotFound(
                f"Cannot bridge '{cap_name}' — "
                f"not registered in zone '{self._zone_name}'."
            )
        target = self._zones.get(to)
        if target is None:
            raise ValueError(f"Zone '{to}' does not exist.")
        target._bridged[cap_name] = self._caps[cap_name]

    # ── Lifecycle ─────────────────────────────────────────

    def boot(self, env: str = "dev", session: Optional[str] = None) -> None:
        if self._frozen:
            diagnostic = {
                "error_type": "core_frozen",
                "message": "boot() called on an already-booted core.",
                "attempted": "core.boot()",
                "fix": [
                    "boot() should only be called once, at the "
                    "end of your boot.py.",
                    "If you're seeing this in a test, use Core.test() "
                    "instead of manually calling boot().",
                    "If multiple modules are trying to boot, you have "
                    "a wiring problem — only one entry point should "
                    "boot the core.",
                ],
                "state": {
                    "frozen": True,
                    "registered": list(self._caps.keys()),
                    "run_id": (self._context.run_id
                               if self._context else "unknown"),
                    "booted_at": (self._context.booted_at
                                  if self._context else "unknown"),
                },
            }
            self._fire_error(diagnostic)
            raise CoreFrozen("Core is already booted.")
        self._validate_expectations()
        self._context = RunContext(env=env, session=session)
        self._frozen = True
        for hook in self._boot_hooks:
            try:
                hook(self)
            except Exception:
                pass

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def shutdown(self) -> dict[str, int]:
        return self.hits

    # ── Test harness ──────────────────────────────────────

    @classmethod
    def test(cls, **overrides: Any) -> "Core":
        audit = overrides.pop("audit", False)
        c = cls(audit=audit)
        c.config = overrides.pop("config", {})
        env = overrides.pop("env", "test")
        for k, v in overrides.items():
            dotted = k.replace("_", ".")
            c.register(dotted, v)
        c.boot(env=env)
        return c

    # ── Named zones ───────────────────────────────────────

    _zones: dict[str, "Core"] = {}

    @classmethod
    def zone(cls, name: str, **kwargs) -> "Core":
        if name in cls._zones:
            return cls._zones[name]
        c = cls(**kwargs)
        c._zone_name = name
        cls._zones[name] = c
        return c

    @classmethod
    def _reset_zones(cls) -> None:
        cls._zones.clear()
        cls._instance = None

    # ── Singleton (backward compatible) ───────────────────

    _instance: Optional["Core"] = None

    @classmethod
    def boot_once(cls, setup_fn) -> "Core":
        if "default" in cls._zones:
            return cls._zones["default"]
        if cls._instance is not None:
            return cls._instance
        c = cls()
        c._zone_name = "default"
        setup_fn(c)
        if not c.is_frozen:
            raise CoreNotBooted(
                "setup_fn must call core.boot() before returning."
            )
        cls._zones["default"] = c
        cls._instance = c
        return c

    @classmethod
    def instance(cls) -> "Core":
        if "default" in cls._zones:
            return cls._zones["default"]
        if cls._instance is not None:
            return cls._instance
        raise CoreNotBooted(
            "No spine instance exists. Call Core.boot_once() "
            "from your entry point before accessing Core.instance()."
        )

    @classmethod
    def _reset_instance(cls) -> None:
        cls._instance = None
        cls._zones.pop("default", None)


# ── Helpers ───────────────────────────────────────────────

def _edit_distance(a: str, b: str) -> int:
    if len(a) < len(b):
        return _edit_distance(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(
                prev[j + 1] + 1,
                curr[j] + 1,
                prev[j] + (0 if ca == cb else 1),
            ))
        prev = curr
    return prev[len(b)]
