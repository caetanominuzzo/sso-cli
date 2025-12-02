"""Config management"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


class SSOConfigManager:
    def __init__(self):
        self.config_path = self._find_config_path()
    
    def _find_config_path(self) -> Optional[Path]:
        paths = []
        if "SSO_CONFIG_PATH" in os.environ:
            paths.append(Path(os.environ["SSO_CONFIG_PATH"]))
        paths.extend([
            Path.cwd() / "sso_config.yaml",
            Path.home() / "sso_config.yaml",
            Path(__file__).parent.parent / "sso_config.yaml"
        ])
        for path in paths:
            if path.exists():
                return path
        return Path.home() / "sso_config.yaml"
    
    def load(self) -> Dict[str, Any]:
        if not YAML_AVAILABLE:
            raise ImportError("PyYAML required: pip install pyyaml")
        if not self.config_path or not self.config_path.exists():
            return {}
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def save(self, config: Dict[str, Any]) -> bool:
        if not YAML_AVAILABLE:
            raise ImportError("PyYAML required: pip install pyyaml")
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            os.chmod(self.config_path, 0o600)
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

