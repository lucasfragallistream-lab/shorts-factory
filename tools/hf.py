"""Run the HyperFrames skill CLI (plugin-cli.mjs) in a project dir, avoiding shell quoting of the user path.

Usage: python tools/hf.py PROJECT_DIR <hyperframes args...>
"""
import subprocess
import sys
from pathlib import Path

cli = Path.home() / ".claude" / "skills" / "hyperframes" / "scripts" / "plugin-cli.mjs"
proj = Path(sys.argv[1]).resolve()
sys.exit(subprocess.call(["node", str(cli), *sys.argv[2:]], cwd=proj))
