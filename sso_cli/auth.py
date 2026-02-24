"""
SSO authentication core: token retrieval via httpx.
Secrets are fetched exclusively from the system keyring (sso_keyring).
"""

import asyncio
import base64
import json
import logging
import httpx
from typing import Dict, Any, Tuple

from .config import load_config, Environments, EnvironmentUsers
from .secrets import get_secret

logger = logging.getLogger(__name__)

_PASSWORD_CLIENT_ID = "delivery-ops-frontend-client"


class SSOAuthenticator:
    def __init__(self) -> None:
        self.environments: Environments
        self.environment_users: EnvironmentUsers
        self.environments, self.environment_users = load_config()

    def get_user_credentials(self, env_key: str, user_key: str) -> Tuple[str, str, str]:
        """Return (credential1, credential2, auth_type).

        Raises ValueError if the secret is not found in the keyring.
        """
        user = self.environment_users[env_key][user_key]
        auth_type = user["auth_type"]
        secret = get_secret(env_key, user_key)
        if secret is None:
            raise ValueError(
                f"No secret found in keyring for {env_key}/{user_key}. "
                "Run 'sso --setup' (or 'sso --reset') to re-enter credentials."
            )

        if auth_type == "client":
            return user["client_id"], secret, auth_type
        else:
            return user["email"], secret, auth_type

    async def get_token(self, env_key: str, user_key: str) -> str:
        env = self.environments[env_key]
        cred1, cred2, auth_type = self.get_user_credentials(env_key, user_key)
        token_url = f"{env['sso_url']}/protocol/openid-connect/token"

        if auth_type == "client":
            data = {
                "grant_type": "client_credentials",
                "client_id": cred1,
                "client_secret": cred2,
            }
        else:
            data = {
                "grant_type": "password",
                "client_id": _PASSWORD_CLIENT_ID,
                "username": cred1,
                "password": cred2,
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            return response.json()["access_token"]

    @staticmethod
    def extract_user_from_token(token: str) -> Dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = parts[1]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
