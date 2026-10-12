"""Application version metadata.

Single source of truth for the backend version string.  Keep in sync
with ``frontend/src/version.ts`` and the ``AppVersion`` field of
``installer.iss``.
"""
from datetime import datetime, timezone

APP_VERSION = "0.2.0"
BUILD_TIME = datetime.now(timezone.utc).isoformat(timespec="seconds")
