"""Export API schemas without starting the backend or opening database connections.

Run with the backend's uv environment and a dummy OAUTH_ENCRYPTION_KEY.
"""

import argparse
import json
from pathlib import Path

from backend.api import (
    artists_router,
    audio_router,
    auth_router,
    search_router,
    tracks_router,
)
from backend.api.lists import router as lists_router
from fastapi import FastAPI


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    app = FastAPI()
    for router in [
        tracks_router,
        search_router,
        artists_router,
        auth_router,
        audio_router,
        lists_router,
    ]:
        app.include_router(router)
    args.output.write_text(json.dumps(app.openapi(), indent=2) + "\n")


if __name__ == "__main__":
    main()
