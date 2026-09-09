"""Pytest fixtures for mislty test suite."""

import os
import sys
import pytest

# Ensure src is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Ensure headless Qt offscreen platform and disable GLib hijacking in Qt
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QT_NO_GLIB"] = "1"
