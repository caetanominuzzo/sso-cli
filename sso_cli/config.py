"""
YAML config loader/writer.

Schema (no secrets -- passwords and client_secrets live in the OS keyring):

environments:
  dev:
    name: Dev
    sso_url: https://sso.dev.example.com/realms/internal
    users:
      admin@example.com:
        auth_type: user
        email: admin@example.com
      my-client-id:
        auth_type: client
        client_id: my-client-id
"""

import os
import shutil
import logging
import yaml
from datetime import datetime
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

CONFIG_FILENAME = "sso_config.yaml"

Environments = Dict[str, Dict[str, str]]
EnvironmentUsers = Dict[str, Dict[str, Dict[str, Any]]]


def find_config_path() -> str:
    """Return the first existing config file path, defaulting to ~/sso_config.yaml."""
    candidates = [
        os.environ.get("SSO_CONFIG_PATH", ""),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME),
        os.path.expanduser(f"~/{CONFIG_FILENAME}"),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return os.path.expanduser(f"~/{CONFIG_FILENAME}")


def load_config() -> Tuple[Environments, EnvironmentUsers]:
    """Parse sso_config.yaml and return (environments, environment_users).

    Raises FileNotFoundError if no config file exists.
    Raises ValueError on malformed data.
    """
    config_path = find_config_path()
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"No config found at {config_path}. Run 'sso --setup' to create one."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    env_cfg = raw.get("environments", raw)
    if not isinstance(env_cfg, dict):
        raise ValueError("Invalid config: expected a mapping of environments.")

    environments: Environments = {}
    environment_users: EnvironmentUsers = {}

    for env_key, env_data in env_cfg.items():
        if not isinstance(env_data, dict) or not env_data.get("sso_url"):
            raise ValueError(f"Environment '{env_key}' is missing 'sso_url'.")
        environments[env_key] = {
            "name": env_data.get("name", env_key),
            "sso_url": env_data["sso_url"],
        }
        users = env_data.get("users") or {}
        environment_users[env_key] = {}
        _LEGACY = {"password": "user", "client_credentials": "client"}
        for user_key, ud in users.items():
            if not isinstance(ud, dict) or "auth_type" not in ud:
                raise ValueError(f"User '{user_key}' in env '{env_key}' missing 'auth_type'.")
            ud["auth_type"] = _LEGACY.get(ud["auth_type"], ud["auth_type"])
            environment_users[env_key][user_key] = {
                "auth_type": ud["auth_type"],  # "user" or "client"
                "email": ud.get("email"),
                "client_id": ud.get("client_id"),
            }

    return environments, environment_users


def save_config(config: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump({"environments": config}, f,
                  default_flow_style=False, allow_unicode=True, sort_keys=False)


def backup_config(config_path: str) -> str:
    """Move config to a timestamped backup. Returns the backup path."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    directory = os.path.dirname(config_path) or os.path.expanduser("~")
    backup_path = os.path.join(directory, f"backup_{ts}_{os.path.basename(config_path)}")
    shutil.move(config_path, backup_path)
    return backup_path
