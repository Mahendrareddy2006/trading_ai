"""Unified Application Entry Point.

Launches the Trading AI FastAPI Backend, background paper-trading worker,
and WebSocket dispatch service.
Includes pre-flight port binding check to prevent Windows WinError 10048 conflicts.
"""

import socket
import sys
import uvicorn
from trading_ai.config.settings import settings


def is_port_bound(host: str, port: int) -> bool:
    """Checks if the target host and port are already occupied."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        try:
            s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Check for port conflict before startup
    if is_port_bound(settings.HOST, settings.PORT):
        print(f"[ERROR] Port {settings.PORT} is already occupied on {settings.HOST}!")
        print(f"[HINT] A running instance of the Trading AI backend is already active on this port.")
        print(f"[HINT] To stop the existing instance in PowerShell, run:")
        print(f'       Stop-Process -Id (Get-NetTCPConnection -LocalPort {settings.PORT}).OwningProcess -Force')
        sys.exit(1)

    print(f"[START] Launching {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"[INFO] Serving REST API & WebSockets on http://{settings.HOST}:{settings.PORT}")
    print(f"[INFO] Operating Mode: {settings.TRADING_MODE.upper()} (Kill Switch: {settings.SAFE_KILL_SWITCH_ACTIVE})")
    print(f"[INFO] Binance Credentials Detected: {'YES (Ready)' if bool(settings.BINANCE_API_KEY) else 'NO (Paper Sandbox Mode)'}")

    uvicorn.run(
        "trading_ai.api.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
