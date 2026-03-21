"""
SSO authentication core: token retrieval via httpx.
Secrets are fetched exclusively from the system keyring (sso_keyring).
"""

import asyncio
import base64
import json
import logging
import httpx
from typing import Dict, Any, List, Tuple

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
        logger.debug("Fetching secret from keyring for %s/%s (auth_type=%s)", env_key, user_key, auth_type)
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

        logger.debug("POST %s  grant_type=%s", token_url, data["grant_type"])
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            logger.debug("Response: %d %s", response.status_code, response.reason_phrase)
            response.raise_for_status()
            token = response.json()["access_token"]
            logger.debug("Token obtained (%d chars, expires in payload)", len(token))
            return token

    @staticmethod
    def extract_user_from_token(token: str) -> Dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = parts[1]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)

    @staticmethod
    def _extract_roles_from_payload(payload: Dict[str, Any]) -> List[str]:
        roles = []
        if isinstance(payload.get("realm_access"), dict):
            roles.extend(payload["realm_access"].get("roles", []))
        if isinstance(payload.get("resource_access"), dict):
            for resource, access in payload["resource_access"].items():
                if isinstance(access, dict):
                    for role in access.get("roles", []):
                        roles.append(f"{resource}:{role}")
        return sorted(roles)

    async def get_user_roles(self, env_key: str, user_key: str) -> Dict[str, List[str]]:
        env = self.environments[env_key]
        user = self.environment_users[env_key][user_key]
        token = await self.get_token(env_key, user_key)
        base_url = env["sso_url"]

        jwt_roles = self._extract_roles_from_payload(self.extract_user_from_token(token))

        if user["auth_type"] == "client":
            introspect_url = f"{base_url}/protocol/openid-connect/token/introspect"
            logger.debug("POST %s (token introspection)", introspect_url)
            cred1, cred2, _ = self.get_user_credentials(env_key, user_key)
            async with httpx.AsyncClient() as client:
                resp = await client.post(introspect_url, data={
                    "token": token,
                    "client_id": cred1,
                    "client_secret": cred2,
                })
                logger.debug("Introspection response: %d", resp.status_code)
                resp.raise_for_status()
                server_roles = self._extract_roles_from_payload(resp.json())
            return {"jwt": jwt_roles, "introspection": server_roles}
        else:
            userinfo_url = f"{base_url}/protocol/openid-connect/userinfo"
            logger.debug("GET %s", userinfo_url)
            async with httpx.AsyncClient() as client:
                resp = await client.get(userinfo_url, headers={"Authorization": f"Bearer {token}"})
                logger.debug("UserInfo response: %d", resp.status_code)
                resp.raise_for_status()
                server_roles = self._extract_roles_from_payload(resp.json())
            return {"jwt": jwt_roles, "userinfo": server_roles}
