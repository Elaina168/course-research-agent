from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    log_dir = project_root / "outputs"
    log_dir.mkdir(exist_ok=True)

    os.chdir(project_root)
    sys.path.insert(0, str(project_root))

    stdout_log = (log_dir / "web-ui.out.log").open("a", encoding="utf-8", buffering=1)
    stderr_log = (log_dir / "web-ui.err.log").open("a", encoding="utf-8", buffering=1)
    sys.stdout = stdout_log
    sys.stderr = stderr_log

    from study_agent.web_app import run_server

    run_server(host="0.0.0.0", port=8899)


if __name__ == "__main__":
    main()
