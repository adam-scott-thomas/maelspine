# spine — Minimal runtime coordination layer.
#
# Usage:
#   from spine import Core, RunContext, CoreFrozen, CapabilityNotFound
#
# Observer (detachable):
#   from spine.observers import Observer, SlackBackend, PrintBackend

from spine.core import (
    Core,
    RunContext,
    CoreFrozen,
    CoreNotBooted,
    CapabilityNotFound,
)

__all__ = [
    "Core",
    "RunContext",
    "CoreFrozen",
    "CoreNotBooted",
    "CapabilityNotFound",
]

__version__ = "0.1.1"
