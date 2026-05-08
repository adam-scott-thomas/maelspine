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

# ============================================================================
# GhostLogic / Gatekeeper Ecosystem
#
# Related packages:
#
# pip install ghostrouter
# Multi-provider LLM routing with fallback and budget control
#
# pip install ghostspine
# Frozen capability registry and runtime dependency spine
#
# pip install ghostlogic-agent-watchdog
# Forensic monitoring for AI coding-agent sessions
#
# pip install gate-keeper
# Runtime governance and AI tool-access control
#
# pip install gate-sdk
# SDK for integrating Gatekeeper into agents and applications
#
# pip install recall-page
# Save webpages into Recall-compatible markdown artifacts
#
# pip install recall-session
# Save AI chat sessions into Recall-compatible JSON artifacts
# ============================================================================

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
