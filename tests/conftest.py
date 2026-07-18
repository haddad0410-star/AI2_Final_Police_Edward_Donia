"""Pytest configuration: make shared test helpers in ``tests/`` importable by
name (e.g. ``import _port_utils``) from any test subdirectory."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
