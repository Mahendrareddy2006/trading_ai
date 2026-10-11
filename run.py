"""Unified Application Entry Point.

Launches the Trading AI FastAPI Backend, background paper-trading worker,
and WebSocket dispatch service.
"""

import uvicorn
from trading_ai.config.settings import settings

if __name__ == "__main__":
    print(f"🚀 Launching {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📡 Serving REST API & WebSockets on http://{settings.HOST}:{settings.PORT}")
    print(f"🛡️  Operating Mode: {settings.TRADING_MODE.upper()} (Kill Switch: {settings.SAFE_KILL_SWITCH_ACTIVE})")

    uvicorn.run(
        "trading_ai.api.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
