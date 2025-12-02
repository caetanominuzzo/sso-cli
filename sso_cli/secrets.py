"""Secret management via keyring"""

import logging

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

logger = logging.getLogger(__name__)


class SecretManager:
    SERVICE_NAME = "sso-cli"
    
    @staticmethod
    def get_secret_key(environment: str, user_key: str, secret_type: str) -> str:
        return f"{environment}:{user_key}:{secret_type}"
    
    @staticmethod
    def get_secret(environment: str, user_key: str, secret_type: str):
        if not KEYRING_AVAILABLE:
            raise ImportError("keyring required: pip install keyring")
        try:
            key = SecretManager.get_secret_key(environment, user_key, secret_type)
            return keyring.get_password(SecretManager.SERVICE_NAME, key)
        except Exception as e:
            logger.error(f"Keyring error: {e}")
            return None
    
    @staticmethod
    def set_secret(environment: str, user_key: str, secret_type: str, secret: str) -> bool:
        if not KEYRING_AVAILABLE:
            raise ImportError("keyring required: pip install keyring")
        try:
            key = SecretManager.get_secret_key(environment, user_key, secret_type)
            keyring.set_password(SecretManager.SERVICE_NAME, key, secret)
            return True
        except Exception as e:
            logger.error(f"Keyring error: {e}")
            return False
    
    @staticmethod
    def delete_secret(environment: str, user_key: str, secret_type: str) -> bool:
        if not KEYRING_AVAILABLE:
            return False
        try:
            key = SecretManager.get_secret_key(environment, user_key, secret_type)
            keyring.delete_password(SecretManager.SERVICE_NAME, key)
            return True
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str or "item not found" in error_str or "-25300" in error_str:
                return True
            logger.error(f"Keyring error: {e}")
            return False

