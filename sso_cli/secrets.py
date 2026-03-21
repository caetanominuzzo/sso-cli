"""
Secure secret storage via the system keyring.

Passwords and client_secrets are NEVER stored in YAML or environment
variables. This module is the single place that reads/writes them.
"""

import logging
import keyring
import keyring.errors
from typing import Optional

logger = logging.getLogger(__name__)

_SERVICE = "sso-cli"


def _key(env_key: str, user_key: str) -> str:
    return f"{env_key}/{user_key}"


def store_secret(env_key: str, user_key: str, secret: str) -> None:
    """Persist a credential secret in the OS keyring."""
    keyring.set_password(_SERVICE, _key(env_key, user_key), secret)


def get_secret(env_key: str, user_key: str) -> Optional[str]:
    """Retrieve a credential secret from the OS keyring (None if not found)."""
    key = _key(env_key, user_key)
    result = keyring.get_password(_SERVICE, key)
    logger.debug("Keyring lookup %s/%s: %s", _SERVICE, key, "found" if result else "NOT FOUND")
    return result


def delete_secret(env_key: str, user_key: str) -> None:
    """Remove a credential secret from the OS keyring (no-op if absent)."""
    try:
        keyring.delete_password(_SERVICE, _key(env_key, user_key))
    except keyring.errors.PasswordDeleteError:
        pass
