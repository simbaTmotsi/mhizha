"""RUNTIME (offline). Generation backends, prompts, and the model registry.

No module in this package may import a network library. Model weights are placed on the
device at build time or install time, never downloaded at runtime.
"""

from __future__ import annotations
