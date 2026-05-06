"""`netsimu-web` console entry point. Boots uvicorn with the FastAPI app."""
from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FRONTEND_DIST = _REPO_ROOT / "frontend" / "dist"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the NetSimu visual lab.")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000,
                        help="Bind port (default 8000)")
    parser.add_argument("--reload", action="store_true",
                        help="Hot-reload on code changes (dev only)")
    args = parser.parse_args()

    if not _FRONTEND_DIST.is_dir():
        print(
            "[netsimu-web] frontend bundle not found at "
            f"{_FRONTEND_DIST}.\n"
            "Run `make web-build` (or `cd frontend && npm ci && npm run build`)"
            " before starting the server."
        )

    uvicorn.run(
        "netops_sim.web.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
