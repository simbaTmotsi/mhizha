"""RUNTIME (offline). Typed errors. Never raise a bare string in this codebase."""

from __future__ import annotations


class MhizhaError(Exception):
    """Base for every Mhizha error."""


class ConfigError(MhizhaError):
    """config.yaml is missing, malformed, or internally inconsistent."""


class SchemaError(MhizhaError):
    """A document or chunk is missing a required field. See corpus/schema.py."""


class IngestError(MhizhaError):
    """A source document could not be ingested. Carries the quarantine reason."""


class IndexError_(MhizhaError):
    """The index is missing, stale, or built with a different embedder."""


class EmbedderMismatchError(IndexError_):
    """Index embedder id or dimension does not match the configured embedder.

    This is loud on purpose. A silent mismatch produces confident nonsense.
    """


class BackendUnavailableError(MhizhaError):
    """A generation or storage backend was requested but cannot be loaded."""


class BudgetExceededError(MhizhaError):
    """The resolved component set does not fit the active device RAM budget."""


class SafetyViolation(MhizhaError):
    """A generated answer failed a safety rule and must not be displayed."""
