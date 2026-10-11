"""Unified Application Entry Point.

Launches the Trading AI FastAPI Backend, background paper-trading worker,
and WebSocket dispatch service.
Includes pre-flight port binding check to prevent Windows WinError 10048 conflicts.
"""

import os
import socket
import sys
import uvicorn
from trading_ai.config.settings import settings


def is_port_bound(host: str, port: int) -> bool:
    """Checks if the target host and port are already occupied."""
    check_host = "127.0.0.1" if host in ["0.0.0.0", ""] else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        try:
            s.connect((check_host, port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    port = int(os.environ.get("PORT", settings.PORT))
    is_cloud = bool(os.getenv("RENDER") or os.getenv("PORT"))
    host = "0.0.0.0" if is_cloud else settings.HOST

    # Check for port conflict before local startup
    if not is_cloud and is_port_bound(host, port):
        print(f"[ERROR] Port {port} is already occupied on {host}!")
        print(f"[HINT] A running instance of the Trading AI backend is already active on this port.")
        print(f"[HINT] To stop the existing instance in PowerShell, run:")
        print(f'       Stop-Process -Id (Get-NetTCPConnection -LocalPort {port}).OwningProcess -Force')
        sys.exit(1)

    print(f"[START] Launching {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"[INFO] Serving REST API & WebSockets on http://{host}:{port}")
    print(f"[INFO] Operating Mode: {settings.TRADING_MODE.upper()} (Kill Switch: {settings.SAFE_KILL_SWITCH_ACTIVE})")
    print(f"[INFO] Binance Credentials Detected: {'YES (Ready)' if bool(settings.BINANCE_API_KEY) else 'NO (Paper Sandbox Mode)'}")

    uvicorn.run(
        "trading_ai.api.app:app",
        host=host,
        port=port,
        reload=settings.DEBUG and not is_cloud,
        log_level="info"
    )
