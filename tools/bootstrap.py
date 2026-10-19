#!/usr/bin/env python3
"""Prepare an isolated checkout for Codex; final stdout is machine-readable JSON."""
from __future__ import annotations

import json
from pathlib import Path
import stat
import subprocess
import sys


PROBE = r'''
import json, pathlib, re, sys
import codex_various_pet, numpy, PIL
def numbers(value):
    return tuple(int(n) for n in re.findall(r"\d+",value)[:2])
if sys.version_info < (3,10):
    raise RuntimeError("Python 3.10+ required")
if numbers(PIL.__version__) < (12,3):
    raise RuntimeError("Pillow 12.3+ required")
if numbers(numpy.__version__) < (1,26):
    raise RuntimeError("NumPy 1.26+ required")
print(json.dumps({"python":sys.executable,"repo":str(pathlib.Path(codex_various_pet.__file__).resolve().parents[2]),"version":codex_various_pet.__version__}))
'''


def main() -> int:
    if sys.version_info < (3, 10):
        raise ValueError("Python 3.10 or newer is required")
    repo = Path(__file__).resolve().parents[1]
    environment = repo / ".venv"
    attributes = getattr(environment.lstat(), "st_file_attributes", 0) if environment.exists() else 0
    if environment.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400) or not environment.resolve().is_relative_to(repo):
        raise ValueError("The checkout's .venv must stay inside this repository")
    interpreter = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not interpreter.exists():
        if environment.exists():
            raise ValueError("Existing .venv has no Python interpreter; inspect it instead of replacing it")
        subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True, stdout=sys.stderr)
    probe = subprocess.run([str(interpreter), "-c", PROBE], capture_output=True, text=True)
    ready = False
    if probe.returncode == 0:
        result = json.loads(probe.stdout)
        ready = Path(result["repo"]).resolve() == repo
    if not ready:
        subprocess.run([str(interpreter), "-m", "pip", "install", "-e", str(repo)], check=True, stdout=sys.stderr)
        probe = subprocess.run([str(interpreter), "-c", PROBE], check=True, capture_output=True, text=True)
        result = json.loads(probe.stdout)
        if Path(result["repo"]).resolve() != repo:
            raise ValueError("Installed module does not belong to this checkout")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f"Bootstrap error: {error}")
