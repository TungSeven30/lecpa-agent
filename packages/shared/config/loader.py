"""Configuration file loaders."""

import os
from functools import lru_cache
from pathlib import Path

import yaml

from shared.config.schemas import (
    EmbeddingsConfig,
    FolderRulesConfig,
    ModelRouterConfig,
    OCRConfig,
    TemplatesConfig,
)


def _get_config_dir() -> Path:
    """Get the config directory path."""
    config_dir = os.environ.get("LECPA_CONFIG_DIR")
    if config_dir:
        return Path(config_dir)

    # Default: look for config dir relative to project root
    current = Path(__file__).resolve()
    for parent in current.parents:
        config_path = parent / "config"
        if config_path.is_dir():
            return config_path

    raise FileNotFoundError("Config directory not found")


def _load_yaml(filename: str) -> dict:
    """Load a YAML config file."""
    config_dir = _get_config_dir()
    config_path = config_dir / filename

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _expand_env_vars(data: dict | list | str) -> dict | list | str:
    """Recursively expand environment variables in config values."""
    if isinstance(data, dict):
        return {k: _expand_env_vars(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_expand_env_vars(item) for item in data]
    if isinstance(data, str) and data.startswith("${") and data.endswith("}"):
        env_var = data[2:-1]
        return os.environ.get(env_var, data)
    return data


@lru_cache
def load_model_router_config() -> ModelRouterConfig:
    """Load the model router configuration."""
    data = _load_yaml("model_router.yaml")
    return ModelRouterConfig(**data)


@lru_cache
def load_embeddings_config() -> EmbeddingsConfig:
    """Load the embeddings configuration."""
    data = _load_yaml("embeddings.yaml")
    return EmbeddingsConfig(**data)


@lru_cache
def load_ocr_config() -> OCRConfig:
    """Load the OCR configuration."""
    data = _load_yaml("ocr.yaml")
    return OCRConfig(**data)


@lru_cache
def load_folder_rules_config() -> FolderRulesConfig:
    """Load the folder rules configuration."""
    data = _load_yaml("folder_rules.yaml")
    data = _expand_env_vars(data)
    return FolderRulesConfig(**data)


@lru_cache
def load_templates_config() -> TemplatesConfig:
    """Load templates configuration from metadata.yaml.

    Returns:
        TemplatesConfig with all template definitions

    Raises:
        FileNotFoundError: If metadata.yaml not found
        ValidationError: If schema validation fails
    """
    config_dir = _get_config_dir()
    metadata_path = config_dir / "templates" / "metadata.yaml"

    if not metadata_path.exists():
        raise FileNotFoundError(f"Templates metadata not found: {metadata_path}")

    with open(metadata_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return TemplatesConfig(**data)


def reload_configs() -> None:
    """Clear cached configs to force reload."""
    load_model_router_config.cache_clear()
    load_embeddings_config.cache_clear()
    load_ocr_config.cache_clear()
    load_folder_rules_config.cache_clear()
    load_templates_config.cache_clear()
