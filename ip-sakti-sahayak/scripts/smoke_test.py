"""Isolated API smoke checks. No external model calls or project-log writes."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.test_regressions import ApiTests

if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ApiTests))
    raise SystemExit(0 if result.wasSuccessful() else 1)
