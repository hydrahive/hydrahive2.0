from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def init_repo(workspace: Path) -> bool:
    try:
        subprocess.run(
            ["git", "init", "-q"], cwd=str(workspace), check=True, timeout=10
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning("git init in %s fehlgeschlagen: %s", workspace, e)
        return False
