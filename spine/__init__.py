# spine — Frozen capability registry.
#
# Usage:
#   from spine import Core, RunContext, CoreFrozen, CapabilityNotFound
#
# Observer (detachable):
#   from spine.observers import Observer, SlackBackend, PrintBackend
#
# Forensics (detachable, Heavy+):
#   from spine.forensics import audit_log, provenance, boot_graph, replay

from spine.core import (
    Core,
    RunContext,
    CoreFrozen,
    CoreNotBooted,
    CapabilityNotFound,
    ValidationError,
)

__all__ = [
    "Core",
    "RunContext",
    "CoreFrozen",
    "CoreNotBooted",
    "CapabilityNotFound",
    "ValidationError",
]

__version__ = "0.3.0"
