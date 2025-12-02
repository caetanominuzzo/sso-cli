"""SSO authentication"""

import base64
import json
import httpx
import logging
from typing import Dict, Any, Optional, List, Tuple
from getpass import getpass
from rich.console import Console
from rich.prompt import Prompt

from .config import SSOConfigManager
from .secrets import SecretManager

logger = logging.getLogger(__name__)
console = Console()


class SSOAuthenticator:
    def __init__(self):
        self.config = {}
        self.config_manager = SSOConfigManager()
        self.load_config()
    
    def load_config(self):
        self.config = self.config_manager.load()
        if not self.config:
            self.config = {"environments": {}, "users": {}}
        if "environments" not in self.config:
            self.config["environments"] = {}
        if "users" not in self.config:
            self.config["users"] = {}
    
    def save_config(self) -> bool:
        return self.config_manager.save(self.config)
    
    def get_environments(self) -> Dict[str, Dict[str, str]]:
        return self.config.get("environments", {})
    
    def get_environment(self, env_key: str) -> Optional[Dict[str, str]]:
        return self.get_environments().get(env_key)
    
    def create_environment(self, env_key: str = None) -> Dict[str, str]:
        if not env_key:
            env_key = Prompt.ask("Environment key")
        console.print(f"[dim]Environment '{env_key}' not found. Creating...[/dim]\n")
        sso_domain = Prompt.ask("SSO domain", default=f"sso.{env_key}.com")
        realm = Prompt.ask("Realm", default="master")
        client_id = Prompt.ask("Client ID (optional)", default="").strip()
        
        domain = sso_domain.strip()
        if domain.startswith('https://'):
            domain = domain[8:]
        elif domain.startswith('http://'):
            domain = domain[7:]
        domain = domain.rstrip('/')
        sso_url = f"https://{domain}"
        
        env_config = {"sso_url": sso_url, "realm": realm}
        if client_id:
            env_config["client_id"] = client_id
        if "environments" not in self.config:
            self.config["environments"] = {}
        self.config["environments"][env_key] = env_config
        self.save_config()
        console.print(f"[green]Environment '{env_key}' created[/green]")
        return env_config
    
    def get_sso_url(self, env_key: str = None) -> str:
        if not env_key:
            env_key = Prompt.ask("Environment key")
        env = self.get_environment(env_key)
        if not env:
            env = self.create_environment(env_key)
        return f"{env['sso_url']}/realms/{env['realm']}"
    
    def remove_environment(self, env_key: str) -> bool:
        if "environments" not in self.config:
            return False
        if env_key not in self.config["environments"]:
            return False
        if "users" in self.config and env_key in self.config["users"]:
            for user_key in list(self.config["users"][env_key].keys()):
                SecretManager.delete_secret(env_key, user_key, "password")
                SecretManager.delete_secret(env_key, user_key, "client_secret")
            del self.config["users"][env_key]
        del self.config["environments"][env_key]
        self.save_config()
        return True
    
    def remove_user(self, environment: str, user_key: str) -> bool:
        if "users" not in self.config:
            return False
        if environment not in self.config["users"]:
            return False
        if user_key not in self.config["users"][environment]:
            return False
        del self.config["users"][environment][user_key]
        SecretManager.delete_secret(environment, user_key, "password")
        SecretManager.delete_secret(environment, user_key, "client_secret")
        self.save_config()
        return True
    
    def get_available_users_for_environment(self, environment: str) -> Dict[str, Dict[str, str]]:
        return self.config.get("users", {}).get(environment, {})
    
    def find_user_by_key(self, environment: str, user_key: str) -> Optional[str]:
        users = self.get_available_users_for_environment(environment)
        if user_key in users:
            return user_key
        for key, config in users.items():
            email = config.get("email", "")
            if email and email.split("@")[0] == user_key:
                return key
        
        matches = []
        for key, config in users.items():
            email = config.get("email", "")
            client_id = config.get("client_id", "")
            if (key.startswith(user_key) or 
                (email and email.split("@")[0].startswith(user_key)) or
                (client_id and client_id.startswith(user_key))):
                display = email or client_id or key
                matches.append((key, display))
        
        if len(matches) == 1:
            return matches[0][0]
        return None
    
    def find_users_by_prefix(self, environment: str, prefix: str) -> List[Tuple[str, str]]:
        users = self.get_available_users_for_environment(environment)
        matches = []
        for key, config in users.items():
            email = config.get("email", "")
            client_id = config.get("client_id", "")
            display = email or client_id or key
            
            if (key.startswith(prefix) or 
                (email and email.split("@")[0].startswith(prefix)) or
                (client_id and client_id.startswith(prefix))):
                matches.append((key, display))
        return matches
    
    def find_environment_by_prefix(self, prefix: str) -> Optional[str]:
        envs = self.get_environments()
        matches = [key for key in envs.keys() if key.startswith(prefix)]
        if len(matches) == 1:
            return matches[0]
        return None
    
    def find_environments_by_prefix(self, prefix: str) -> List[str]:
        envs = self.get_environments()
        return [key for key in envs.keys() if key.startswith(prefix)]
    
    def get_user_credentials(self, environment: str, user_key: str) -> tuple[str, str, str]:
        if "users" not in self.config:
            self.config["users"] = {}
        if environment not in self.config["users"]:
            self.config["users"][environment] = {}
        
        actual_key = self.find_user_by_key(environment, user_key)
        if not actual_key:
            actual_key = user_key
        
        if actual_key not in self.config["users"][environment]:
            if "@" in actual_key:
                self.config["users"][environment][actual_key] = {
                    "auth_type": "password",
                    "email": actual_key
                }
                password = getpass(f"Password for {actual_key}: ")
                SecretManager.set_secret(environment, actual_key, "password", password)
                console.print("[green]Saved to keyring[/green]")
            else:
                self.config["users"][environment][actual_key] = {
                    "auth_type": "client_credentials",
                    "client_id": actual_key
                }
                client_secret = getpass(f"Client Secret for {actual_key}: ")
                SecretManager.set_secret(environment, actual_key, "client_secret", client_secret)
                console.print("[green]Saved to keyring[/green]")
            self.save_config()
        
        user_config = self.config["users"][environment][actual_key]
        auth_type = user_config.get("auth_type", "password")
        
        if auth_type == "client_credentials":
            client_id = user_config.get("client_id")
            if not client_id:
                raise ValueError(f"Missing client_id for {actual_key}")
            client_secret = SecretManager.get_secret(environment, actual_key, "client_secret")
            if not client_secret:
                client_secret = getpass(f"Client Secret for {client_id}: ")
                SecretManager.set_secret(environment, actual_key, "client_secret", client_secret)
                console.print("[green]Saved to keyring[/green]")
            return client_id, client_secret, auth_type
        else:
            email = user_config.get("email")
            if not email:
                raise ValueError(f"Missing email for {actual_key}")
            password = SecretManager.get_secret(environment, actual_key, "password")
            if not password:
                password = getpass(f"Password for {email}: ")
                SecretManager.set_secret(environment, actual_key, "password", password)
                console.print("[green]Saved to keyring[/green]")
            return email, password, auth_type
    
    async def get_token(self, environment: str, user_key: str) -> str:
        sso_url = self.get_sso_url(environment)
        cred1, cred2, auth_type = self.get_user_credentials(environment, user_key)
        token_url = f"{sso_url}/protocol/openid-connect/token"
        env_config = self.get_environment(environment) or {}
        client_id = env_config.get("client_id")
        
        if auth_type == "client_credentials":
            data = {"grant_type": "client_credentials", "client_id": cred1, "client_secret": cred2}
        else:
            data = {"grant_type": "password", "username": cred1, "password": cred2}
            if client_id:
                data["client_id"] = client_id
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=data)
                if response.status_code == 401:
                    if auth_type == "password":
                        if not client_id:
                            console.print("[yellow]This environment may require a client_id.[/yellow]")
                            new_client_id = Prompt.ask("Client ID (or press Enter to skip)", default="").strip()
                            if new_client_id:
                                env_config = self.get_environment(environment) or {}
                                env_config["client_id"] = new_client_id
                                if "environments" not in self.config:
                                    self.config["environments"] = {}
                                self.config["environments"][environment] = env_config
                                self.save_config()
                                client_id = new_client_id
                                console.print("[green]Client ID saved[/green]")
                        
                        console.print("[yellow]Auth failed. Enter new password (or press Enter to retry with same):[/yellow]")
                        new_password = getpass(f"Password for {cred1}: ")
                        if new_password:
                            SecretManager.set_secret(environment, user_key, "password", new_password)
                            console.print("[green]Saved to keyring[/green]")
                            data = {"grant_type": "password", "username": cred1, "password": new_password}
                        else:
                            data = {"grant_type": "password", "username": cred1, "password": cred2}
                        if client_id:
                            data["client_id"] = client_id
                    else:
                        console.print("[yellow]Auth failed. Enter new client secret (or press Enter to retry with same):[/yellow]")
                        new_secret = getpass(f"Client Secret for {cred1}: ")
                        if new_secret:
                            SecretManager.set_secret(environment, user_key, "client_secret", new_secret)
                            console.print("[green]Saved to keyring[/green]")
                            data = {"grant_type": "client_credentials", "client_id": cred1, "client_secret": new_secret}
                        else:
                            data = {"grant_type": "client_credentials", "client_id": cred1, "client_secret": cred2}
                    async with httpx.AsyncClient() as retry_client:
                        retry_response = await retry_client.post(token_url, data=data)
                        retry_response.raise_for_status()
                        return retry_response.json()["access_token"]
                response.raise_for_status()
                return response.json()["access_token"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Authentication failed")
            raise
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
    
    def _decode_jwt_payload(self, token: str) -> Dict[str, Any]:
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return {}
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4) if len(payload) % 4 else ''
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception:
            return {}
    
    def _extract_roles_from_payload(self, payload: Dict[str, Any]) -> List[str]:
        roles = []
        if "realm_access" in payload and isinstance(payload["realm_access"], dict):
            if "roles" in payload["realm_access"]:
                roles.extend(payload["realm_access"]["roles"])
        if "resource_access" in payload and isinstance(payload["resource_access"], dict):
            for resource, access in payload["resource_access"].items():
                if isinstance(access, dict) and "roles" in access:
                    for role in access["roles"]:
                        roles.append(f"{resource}:{role}")
        return sorted(roles)
    
    async def get_user_roles(self, environment: str, user_key: str) -> Dict[str, List[str]]:
        token = await self.get_token(environment, user_key)
        jwt_payload = self._decode_jwt_payload(token)
        jwt_roles = self._extract_roles_from_payload(jwt_payload)
        
        sso_url = self.get_sso_url(environment)
        userinfo_url = f"{sso_url}/protocol/openid-connect/userinfo"
        headers = {"Authorization": f"Bearer {token}"}
        userinfo_roles = []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(userinfo_url, headers=headers)
                response.raise_for_status()
                userinfo = response.json()
                userinfo_roles = self._extract_roles_from_payload(userinfo)
        except Exception as e:
            logger.error(f"Error fetching userinfo: {e}")
        
        return {
            "jwt": jwt_roles,
            "userinfo": userinfo_roles
        }

