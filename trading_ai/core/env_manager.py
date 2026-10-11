"""Safe environment variable and .env management service.

Handles:
- Detecting whether application is running locally vs deployed in cloud (e.g. Render / Vercel)
- Controlled, atomic updates to whitelisted environment variables in local development
- Preserving all unrelated variables, comments, and file structure
- Preventing arbitrary file writing or secret leaks in logs
"""

import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Optional, Set, Tuple

from trading_ai.config.settings import PROJECT_ROOT, ENV_FILE_PATH, settings
from trading_ai.core.logging import get_logger

logger = get_logger("EnvManager")

# Whitelist of keys that can be updated via the administrative configuration flow
ALLOWED_ENV_KEYS: Set[str] = {
    "WHATSAPP_API_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_ENABLED",
    "WHATSAPP_PROVIDER",
    "WHATSAPP_FROM_NUMBER",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "TELEGRAM_ENABLED",
    "CORS_ORIGINS",
    "IN_APP_NOTIFICATIONS_ENABLED"
}


def is_cloud_environment() -> bool:
    """Detects if running on Render, Vercel, Heroku, or containerized cloud."""
    return bool(
        os.getenv("RENDER") or 
        os.getenv("VERCEL") or 
        os.getenv("DYNO") or 
        os.getenv("KUBERNETES_SERVICE_HOST") or
        os.getenv("FLY_APP_NAME")
    )


def is_env_file_writable() -> bool:
    """Returns True if running locally and root .env is accessible and writable."""
    if is_cloud_environment():
        return False
    try:
        if ENV_FILE_PATH.exists():
            return os.access(ENV_FILE_PATH, os.W_OK)
        else:
            parent = ENV_FILE_PATH.parent
            return os.access(parent, os.W_OK)
    except Exception:
        return False


def get_deployment_context() -> Dict[str, Any]:
    """Returns metadata about the current runtime deployment and environment."""
    cloud = is_cloud_environment()
    platform = "local"
    if os.getenv("RENDER"):
        platform = "render"
    elif os.getenv("VERCEL"):
        platform = "vercel"
    elif cloud:
        platform = "cloud"

    return {
        "platform": platform,
        "is_cloud": cloud,
        "env_writable": is_env_file_writable(),
        "env_file_exists": ENV_FILE_PATH.exists(),
        "env_path": str(ENV_FILE_PATH) if not cloud else "managed_in_cloud_dashboard"
    }


def update_whitelisted_env_keys(updates: Dict[str, str]) -> Tuple[bool, str]:
    """Atomically updates whitelisted keys in the local root .env file.
    
    Preserves all comments, blank lines, and existing non-whitelisted keys.
    Updates in-memory os.environ and Pydantic settings attributes immediately.
    """
    if is_cloud_environment():
        return False, (
            "Cloud deployment detected (e.g. Render). "
            "Please configure environment variables directly in your Render Service Dashboard → Environment."
        )

    # Validate all requested keys are in whitelist
    invalid_keys = [k for k in updates.keys() if k not in ALLOWED_ENV_KEYS]
    if invalid_keys:
        return False, f"Unauthorized environment variable modification attempted: {', '.join(invalid_keys)}"

    # Read existing .env if present
    existing_lines = []
    if ENV_FILE_PATH.exists():
        try:
            with open(ENV_FILE_PATH, "r", encoding="utf-8") as f:
                existing_lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to read existing .env: {e}")
            return False, f"Failed to read existing configuration: {str(e)}"

    new_lines = []
    keys_handled = set()

    # Rewrite lines, updating existing keys in place and preserving comments
    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        if "=" in line:
            key, _ = line.split("=", 1)
            key = key.strip()
            if key in updates:
                new_value = updates[key]
                new_lines.append(f"{key}={new_value}\n")
                keys_handled.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Append any new keys that were not previously present in .env
    for key, value in updates.items():
        if key not in keys_handled:
            new_lines.append(f"{key}={value}\n")

    # Atomic write via temporary file
    temp_dir = ENV_FILE_PATH.parent
    try:
        with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tmp_file:
            tmp_file.writelines(new_lines)
            temp_path = Path(tmp_file.name)

        # Replace existing .env atomically
        temp_path.replace(ENV_FILE_PATH)
        logger.info(f"Successfully updated keys in {ENV_FILE_PATH}: {list(updates.keys())}")

        # Update os.environ and in-memory settings
        for key, val in updates.items():
            os.environ[key] = str(val)
            if hasattr(settings, key):
                target_type = type(getattr(settings, key))
                try:
                    if target_type == bool:
                        setattr(settings, key, str(val).lower() in ("true", "1", "yes"))
                    elif target_type == int:
                        setattr(settings, key, int(val))
                    elif target_type == float:
                        setattr(settings, key, float(val))
                    else:
                        setattr(settings, key, str(val))
                except Exception as ex:
                    logger.warning(f"Could not convert setting {key} to {target_type}: {ex}")

        return True, "Configuration successfully saved and applied."

    except Exception as e:
        logger.error(f"Atomic write to .env failed: {e}")
        return False, f"Failed to save configuration: {str(e)}"
