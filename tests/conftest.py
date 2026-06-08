from pathlib import Path
import shutil
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _bash_usable() -> bool:
    bash = shutil.which("bash")
    if not bash:
        return False
    try:
        result = subprocess.run(
            [bash, "-lc", "true"],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    """Windows machines may expose a WSL relay named bash while /bin/bash is absent.

    The web shell-script tests exercise Linux/macOS installers, not the Windows
    Antigravity Desktop package. Skip them when bash cannot actually execute.
    """
    bash_ok = _bash_usable()
    skip_bash = pytest.mark.skip(reason="bash is not usable on this Windows host")
    for item in items:
        if not bash_ok and "test_web_scripts.py" in str(item.fspath):
            item.add_marker(skip_bash)
