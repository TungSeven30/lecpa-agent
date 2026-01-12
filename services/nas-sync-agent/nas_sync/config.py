"""Configuration loading for NAS sync agent."""

import os
from pathlib import Path

import yaml

from nas_sync.models import Config


def load_config(config_path: str | Path = "config.yaml") -> Config:
    """Load configuration from YAML file with environment variable substitution.

    Args:
        config_path: Path to the configuration YAML file

    Returns:
        Validated Config object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(path) as f:
        raw_config = yaml.safe_load(f)

    # Substitute environment variables (${VAR_NAME} syntax)
    config_str = yaml.dump(raw_config)
    config_str = _substitute_env_vars(config_str)
    config_data = yaml.safe_load(config_str)

    return Config(**config_data)


def _substitute_env_vars(text: str) -> str:
    """Substitute ${VAR_NAME} with environment variable values.

    Args:
        text: String containing ${VAR_NAME} patterns

    Returns:
        String with environment variables substituted
    """
    import re

    pattern = r"\$\{([^}]+)\}"

    def replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        value = os.environ.get(var_name, "")
        if not value:
            # Check if it's a required variable (doesn't have a default)
            return match.group(0)  # Return original if not set
        return value

    return re.sub(pattern, replace, text)


def get_default_config() -> dict:
    """Return default configuration as a dictionary.

    This can be used to generate a config.yaml.example file.

    Returns:
        Default configuration dictionary
    """
    return {
        "nas": {
            "root_path": "/volume1/LeCPA/ClientFiles",
            "watch_recursive": True,
            "debounce_seconds": 2,
        },
        "api": {
            "base_url": "http://lecpa-api:8000",
            "api_key": "${SYNC_AGENT_API_KEY}",
            "timeout_seconds": 30,
            "retry_attempts": 3,
        },
        "parsing": {
            "client_patterns": [
                {"pattern": r"^(?P<code>1\d{3})_(?P<name>.+)$", "type": "individual"},
                {"pattern": r"^(?P<code>2\d{3})_(?P<name>.+)$", "type": "business"},
            ],
            "year_pattern": r"^(?P<year>20\d{2})$",
            "special_folders": [
                {"folder": "Permanent", "tag": "permanent", "is_permanent": True},
                {"folder": "Tax Notice", "tag": "tax_notice"},
                {"folder": "Tax Transcript", "tag": "transcript"},
                {"folder": "Tax Emails", "tag": "emails"},
                {"folder": "Paperworks", "tag": "paperwork"},
                {"folder": "Invoice", "tag": "invoice"},
                {"folder": "IRS Notices", "tag": "irs_notice"},
            ],
            "skip_patterns": [
                "*.7z",
                "*.zip",
                "*.rar",
                "*.lnk",
                ".DS_Store",
                "Thumbs.db",
                "Icon*",
                "*.tmp",
                "~$*",
            ],
            "document_tags": [
                {"pattern": r"(?i)w-?2", "tag": "W2"},
                {"pattern": r"(?i)1099", "tag": "1099"},
                {"pattern": r"(?i)k-?1|k1p|k1s", "tag": "K1"},
                {"pattern": r"(?i)1098", "tag": "1098"},
                {"pattern": r"(?i)notice|cp\s?\d+|lt\s?\d+", "tag": "IRS_NOTICE"},
                {"pattern": r"(?i)transcript", "tag": "TRANSCRIPT"},
            ],
        },
        "state": {
            "db_path": "/app/state/sync_state.db",
        },
        "digest": {
            "enabled": True,
            "send_time": "08:00",
            "recipients": ["admin@lecpa.com"],
            "smtp": {
                "host": "${SMTP_HOST}",
                "port": 587,
                "user": "${SMTP_USER}",
                "password": "${SMTP_PASSWORD}",
            },
        },
        "logging": {
            "level": "INFO",
            "format": "json",
        },
    }
