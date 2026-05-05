"""Gateway configuration — file-based config in ~/.riskmanaged/.

No database. All configuration is stored as YAML files:
- ~/.riskmanaged/config.yaml          Global config (API key, bridge URL)
- ~/.riskmanaged/exchanges/<label>.yaml  Per-exchange credentials
"""

import os
import stat
from pathlib import Path
from typing import Optional

import yaml

from gateway.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_DIR = Path.home() / ".riskmanaged"
DEFAULT_BRIDGE_URL = "wss://bridge.riskmanaged.io/bridge/ws/gateway"


def get_config_dir() -> Path:
    """Return the config directory, respecting RISKMANAGED_HOME env var."""
    return Path(os.environ.get("RISKMANAGED_HOME", str(DEFAULT_CONFIG_DIR)))


def get_exchanges_dir() -> Path:
    """Return the exchanges config directory."""
    return get_config_dir() / "exchanges"


# ---------------------------------------------------------------------------
# Global config
# ---------------------------------------------------------------------------


class GatewayConfig:
    """Global gateway configuration loaded from config.yaml."""

    def __init__(
        self,
        api_key: str = "",
        bridge_url: str = DEFAULT_BRIDGE_URL,
        log_level: str = "INFO",
    ):
        self.api_key = api_key
        self.bridge_url = bridge_url
        self.log_level = log_level

    @classmethod
    def load(cls) -> "GatewayConfig":
        """Load config from ~/.riskmanaged/config.yaml."""
        config_path = get_config_dir() / "config.yaml"
        if not config_path.exists():
            return cls()

        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

        return cls(
            api_key=raw.get("api_key", ""),
            bridge_url=raw.get("bridge_url", DEFAULT_BRIDGE_URL),
            log_level=raw.get("log_level", "INFO"),
        )

    def save(self):
        """Save config to ~/.riskmanaged/config.yaml."""
        config_dir = get_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        _secure_dir(config_dir)

        config_path = config_dir / "config.yaml"
        data = {
            "api_key": self.api_key,
            "bridge_url": self.bridge_url,
            "log_level": self.log_level,
        }
        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
        _secure_file(config_path)

    @property
    def is_configured(self) -> bool:
        """Check if the gateway has been bootstrapped."""
        return bool(self.api_key)


# ---------------------------------------------------------------------------
# Exchange config
# ---------------------------------------------------------------------------


class ExchangeConfig:
    """A single exchange credential configuration."""

    def __init__(
        self,
        id: str,
        exchange_name: str,
        label: str,
        api_key: str,
        api_secret: str,
        password: Optional[str] = None,
        sandbox: bool = False,
    ):
        self.id = id
        self.exchange_name = exchange_name
        self.label = label
        self.api_key = api_key
        self.api_secret = api_secret
        self.password = password
        self.sandbox = sandbox

    @classmethod
    def from_file(cls, path: Path) -> "ExchangeConfig":
        """Load an exchange config from a YAML file."""
        with open(path) as f:
            raw = yaml.safe_load(f) or {}

        return cls(
            id=raw.get("id", ""),
            exchange_name=raw.get("exchange_name", ""),
            label=raw.get("label", path.stem),
            api_key=raw.get("api_key", ""),
            api_secret=raw.get("api_secret", ""),
            password=raw.get("password"),
            sandbox=raw.get("sandbox", False),
        )

    def save(self):
        """Save exchange config to ~/.riskmanaged/exchanges/<label>.yaml."""
        exchanges_dir = get_exchanges_dir()
        exchanges_dir.mkdir(parents=True, exist_ok=True)

        path = exchanges_dir / f"{self.label}.yaml"
        data = {
            "id": self.id,
            "exchange_name": self.exchange_name,
            "label": self.label,
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "password": self.password,
            "sandbox": self.sandbox,
        }
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
        _secure_file(path)

    def delete(self):
        """Delete this exchange config file."""
        path = get_exchanges_dir() / f"{self.label}.yaml"
        if path.exists():
            path.unlink()

    def to_registration_dict(self) -> dict:
        """Serialize for bridge registration (no secrets sent to platform)."""
        return {
            "id": self.id,
            "exchange_name": self.exchange_name,
            "label": self.label,
            "sandbox": self.sandbox,
        }


def load_all_exchanges() -> list[ExchangeConfig]:
    """Load all exchange configs from ~/.riskmanaged/exchanges/."""
    exchanges_dir = get_exchanges_dir()
    if not exchanges_dir.exists():
        return []

    configs = []
    for path in sorted(exchanges_dir.glob("*.yaml")):
        try:
            configs.append(ExchangeConfig.from_file(path))
        except Exception as e:
            logger.error("Failed to load exchange config", path=str(path), error=str(e))

    return configs


# ---------------------------------------------------------------------------
# File security helpers
# ---------------------------------------------------------------------------


def _secure_dir(path: Path):
    """Set directory permissions to 700 (owner only)."""
    try:
        path.chmod(stat.S_IRWXU)
    except OSError:
        pass


def _secure_file(path: Path):
    """Set file permissions to 600 (owner read/write only)."""
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
