# ══════════════════════════════════════════════════════════
# forensics.py — Detachable forensic utilities for spine Heavy+
# Part of the `spine` package
# ══════════════════════════════════════════════════════════
#
# FOR AI ASSISTANTS:
#   This module is FULLY DETACHABLE from core.py. The core has
#   zero imports from this file. Delete it and spine still works.
#
# WHAT THIS IS
# ──────────────────────────────────────────────────────────
# Convenience functions that read from Core's attributes to
# answer forensic questions:
#
#   Who registered what, from where?     provenance(core)
#   Who accessed what, when?             audit_log(core)
#   What depends on what?                boot_graph(core)
#   Rebuild this exact state?            replay(snapshot)
#   Load from disk?                      from_export(path)
#
# RELATIONSHIP TO CORE
# ──────────────────────────────────────────────────────────
# These functions read from Core's semi-public attributes:
#   core._audit_log      (list of get() access records)
#   core._provenance     (dict of register() caller records)
#   core._expectations   (dict of expect() declarations)
#   core._caps           (the capability registry)
#
# Core populates these when audit=True. This module just
# provides filtered views, exports, and replay.
#
# USAGE
# ──────────────────────────────────────────────────────────
#   from spine import Core
#   from spine.forensics import audit_log, provenance, boot_graph
#
#   c = Core(audit=True)
#   c.register("db.conn", conn)
#   c.register("cache", redis)
#   c.expect("svc.a", requires=["db.conn"])
#   c.boot()
#   c.get("db.conn")
#
#   audit_log(c)                   # all get() records
#   audit_log(c, cap="db.conn")   # filtered by capability
#   provenance(c, name="db.conn") # who registered it
#   boot_graph(c)                  # dependency graph
#   replay(c.snapshot())           # frozen clone
#
# ══════════════════════════════════════════════════════════

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from spine import Core


# ── Audit log ─────────────────────────────────────────────

def audit_log(core: "Core", *, cap: str = None,
              caller: str = None) -> list[dict[str, Any]]:
    """Filtered view of the core's audit log.

    Returns list of dicts with: cap, caller, function, at, hit.
    """
    log = core._audit_log
    if cap is not None:
        log = [e for e in log if e["cap"] == cap]
    if caller is not None:
        log = [e for e in log if caller in e.get("caller", "")]
    return list(log)


# ── Provenance ────────────────────────────────────────────

def provenance(core: "Core", *, name: str = None) -> dict[str, Any]:
    """Who registered what, from where, when.

    Returns dict with: source, function, registered_at.
    If name is None, returns all provenance records.
    """
    if name is not None:
        return dict(core._provenance.get(name, {}))
    return dict(core._provenance)


# ── Boot graph ────────────────────────────────────────────

def boot_graph(core: "Core") -> dict[str, Any]:
    """Dependency graph from expectations.

    Returns dict with:
      nodes — sorted list of registered capability names
      edges — list of {"from": name, "to": dep}
      zone  — zone name or None
    """
    nodes = sorted(core._caps.keys())
    edges = []
    for name, exp in core._expectations.items():
        for dep in exp.get("requires", []):
            edges.append({"from": name, "to": dep})
    return {
        "nodes": nodes,
        "edges": edges,
        "zone": core._zone_name,
    }


# ── Replay ────────────────────────────────────────────────

def replay(snapshot: dict) -> "Core":
    """Reconstruct a frozen Core from a snapshot dict.

    Non-serializable capabilities that were stored as repr()
    remain as strings. Re-register complex objects after replay.
    """
    from spine.core import Core, RunContext

    c = Core()
    c._zone_name = snapshot.get("zone")
    for name, value in snapshot.get("capabilities", {}).items():
        c._caps[name] = value
        c._hits[name] = 0
    c._context = RunContext(
        run_id=snapshot.get("run_id", str(uuid4())),
        booted_at=snapshot.get(
            "booted_at", datetime.now(timezone.utc).isoformat()
        ),
        env=snapshot.get("env", "dev"),
        session=snapshot.get("session"),
    )
    c._frozen = True
    return c


def from_export(path: str) -> "Core":
    """Load a frozen Core from a JSON file."""
    with open(path) as f:
        snapshot = json.load(f)
    return replay(snapshot)
