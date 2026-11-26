"""Acquire and validate the research panel. Credentials come from the environment."""
import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.argv.insert(1, "--download-only")
    runpy.run_path(str(Path(__file__).with_name("02_dupor_hogan_jp.py")), run_name="__main__")
