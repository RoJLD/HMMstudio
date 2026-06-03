"""Build the React frontend and copy the output into the server's static/ dir.

Usage:
    python scripts/build_frontend.py

Requires `npm` on PATH. Run from the repo root.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# On Windows, `npm` is a `.cmd` shim that needs shell=True to be resolved via
# PATH. On Linux / macOS, `shell=True` with a list-arg silently drops every
# argument past the first (the shell receives only `npm` and treats the rest
# as $0, $1...), so `npm install` becomes a bare `npm` that prints help and
# exits 1. Use the shell only where it's actually required.
_NEEDS_SHELL = sys.platform == "win32"


def main() -> int:
    repo_root = Path(__file__).parent.parent
    frontend = repo_root / "src" / "hmm_studio" / "frontend"
    static_dst = repo_root / "src" / "hmm_studio" / "server" / "static"

    if not (frontend / "package.json").exists():
        print(f"ERROR: no package.json at {frontend}", file=sys.stderr)
        return 1

    print(f"[1/3] npm install in {frontend}...")
    subprocess.run(["npm", "install"], cwd=frontend, check=True, shell=_NEEDS_SHELL)

    print(f"[2/3] npm run build in {frontend}...")
    subprocess.run(["npm", "run", "build"], cwd=frontend, check=True, shell=_NEEDS_SHELL)

    src = frontend / "dist"
    if not src.exists():
        print(f"ERROR: build output not found at {src}", file=sys.stderr)
        return 1

    print(f"[3/3] copying {src} -> {static_dst}")
    if (static_dst / "assets").exists():
        shutil.rmtree(static_dst / "assets")
    if (static_dst / "index.html").exists():
        (static_dst / "index.html").unlink()
    shutil.copytree(src / "assets", static_dst / "assets")
    shutil.copy2(src / "index.html", static_dst / "index.html")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
