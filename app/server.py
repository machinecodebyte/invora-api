from __future__ import annotations

import logging
import socket
import sys

import uvicorn

from app.core.config import get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)

FALLBACK_PORTS = (8000, 8001, 8002, 8010)


def resolve_api_port(host: str, configured_port: int) -> int:
    candidates = (configured_port,) + tuple(
        port for port in FALLBACK_PORTS if port != configured_port
    )
    for port in candidates:
        if _is_port_available(host, port):
            if port != configured_port:
                logger.warning(
                    "configured_api_port_unavailable",
                    extra={"api_host": host, "api_port": port},
                )
            return port

    options = ", ".join(str(port) for port in candidates)
    msg = f"No available API port found. Checked: {options}"
    raise RuntimeError(msg)


def _is_port_available(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind((host, port))
    except OSError:
        return False
    return True


def main() -> int:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    api_port = resolve_api_port(settings.API_HOST, settings.API_PORT)
    startup_context = settings.startup_log_context
    startup_context["api_port"] = api_port
    logger.info(
        "api_server_starting",
        extra={"app_name": settings.APP_NAME, **startup_context},
    )
    from app.main import app

    app.state.api_port = api_port
    uvicorn.run(app, host=settings.API_HOST, port=api_port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
