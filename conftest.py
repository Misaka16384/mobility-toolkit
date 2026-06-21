"""Pytest bootstrap.

Ensures the repo root is on ``sys.path`` so ``import mobility_toolkit`` resolves
when running ``pytest`` directly from a fresh clone, before ``pip install -e .``.
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
