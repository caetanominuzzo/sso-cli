"""
Secure secret storage via the system keyring.

Passwords and client_secrets are NEVER stored in YAML or environment
variables. This module is the single place that reads/writes them.
"""

import keyring
import keyring.errors
from typing import Optional

_SERVICE = "sso-cli"


def _key(env_key: str, user_key: str) -> str:
    return f"{env_key}/{user_key}"


def store_secret(env_key: str, user_key: str, secret: str) -> None:
    """Persist a credential secret in the OS keyring."""
    keyring.set_password(_SERVICE, _key(env_key, user_key), secret)


def get_secret(env_key: str, user_key: str) -> Optional[str]:
    """Retrieve a credential secret from the OS keyring (None if not found)."""
    return keyring.get_password(_SERVICE, _key(env_key, user_key))


def delete_secret(env_key: str, user_key: str) -> None:
    """Remove a credential secret from the OS keyring (no-op if absent)."""
    try:
        keyring.delete_password(_SERVICE, _key(env_key, user_key))
    except keyring.errors.PasswordDeleteError:
        pass
