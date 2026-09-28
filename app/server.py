from __future__ import annotations

import os
import logging
import socket
import sys

import uvicorn

from app.core.config import get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)

FALLBACK_PORTS = (8000, 8001, 8002, 8010)


def resolve_api_port(
    host: str,
    configured_port: int,
    *,
    allow_fallback: bool = False,
) -> int:
    if not allow_fallback:
        # Let Uvicorn own the bind operation. A preflight socket probe is racy;
        # production must fail loudly instead of silently selecting another port.
        return configured_port

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


# def main() -> int:
#     settings = get_settings()
#     configure_logging(settings.LOG_LEVEL)
#     api_port = resolve_api_port(
#         settings.API_HOST,
#         settings.API_PORT,
#         allow_fallback=settings.API_PORT_FALLBACK_ENABLED,
#     )
#     startup_context = settings.startup_log_context
#     startup_context["api_port"] = api_port
#     logger.info(
#         "api_server_starting",
#         extra={"app_name": settings.APP_NAME, **startup_context},
#     )
#     from app.main import app

#     app.state.api_port = api_port
#     uvicorn.run(app, host=settings.API_HOST, port=api_port)
#     return 0


def main() -> int:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    # Render automatically provides PORT.
    # If PORT exists, bind publicly on 0.0.0.0.
    # Otherwise use the local .env configuration.
    render_port = os.getenv("PORT")

    if render_port:
        api_host = "0.0.0.0"
        configured_port = int(render_port)
        allow_fallback = False
    else:
        api_host = settings.API_HOST
        configured_port = settings.API_PORT
        allow_fallback = settings.API_PORT_FALLBACK_ENABLED

    api_port = resolve_api_port(
        api_host,
        configured_port,
        allow_fallback=allow_fallback,
    )

    startup_context = settings.startup_log_context
    startup_context["api_host"] = api_host
    startup_context["api_port"] = api_port

    logger.info(
        "api_server_starting",
        extra={"app_name": settings.APP_NAME, **startup_context},
    )

    from app.main import app

    app.state.api_port = api_port

    uvicorn.run(
        app,
        host=api_host,
        port=api_port,
    )

    return 0

if __name__ == "__main__":
    sys.exit(main())
