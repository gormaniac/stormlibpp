"""Inspect Stormgen extraction without maintaining a second example document."""

from pathlib import Path
import runpy


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("data") / "test_stormgen.py"), run_name="__main__")
