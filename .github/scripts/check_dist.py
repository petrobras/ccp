"""Check the built distributions before they are published.

    python .github/scripts/check_dist.py dist/

Every file git tracks under the packages (``ccp/`` and ``ccp_web/``: code,
templates, static files, migrations, test data) must be in both the wheel and
the sdist, and no compiled bytecode may be.
"""

import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

PACKAGES = ("ccp", "ccp_web")
ROOT = Path(__file__).resolve().parents[2]


def tracked_files():
    out = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--", *PACKAGES], text=True
    )
    files = {name for name in out.split("\0") if name}
    if not files:
        sys.exit(f"git tracks no files under {', '.join(PACKAGES)} in {ROOT}")
    return files


def check(kind, names, expected):
    errors = [f"{kind}: missing {name}" for name in sorted(expected - names)]
    errors += [f"{kind}: bytecode {name}" for name in sorted(names) if ".pyc" in name]
    print(f"{kind}: {len(names)} files, {len(expected & names)} tracked files found")
    return errors


def main(dist="dist"):
    dist = Path(dist)
    expected = tracked_files()
    (wheel,) = dist.glob("*.whl")
    (sdist,) = dist.glob("*.tar.gz")
    with zipfile.ZipFile(wheel) as zf:
        wheel_names = set(zf.namelist())
    with tarfile.open(sdist) as tf:
        # Members are prefixed with "<name>-<version>/".
        sdist_names = {m.name.split("/", 1)[-1] for m in tf.getmembers()}
    errors = check(wheel.name, wheel_names, expected)
    errors += check(sdist.name, sdist_names, expected)
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
