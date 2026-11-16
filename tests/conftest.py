"""Shared pytest fixtures + sys.path bootstrap.

Adds the project root to sys.path so `from serato_automation...` works without
per-test path hacks.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
