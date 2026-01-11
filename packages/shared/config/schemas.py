"""Pydantic schemas for configuration files."""

from pydantic import BaseModel, Field


class ModelRoute(BaseModel):
    """Configuration for a specific model route."""

    provider: str = "anthropic"
    model: str
    max_tokens: int = 4096
    temperature: float = 0.3


class ProviderConfig(BaseModel):
    """Provider-specific configuration."""

    api_key_env: str
    base_url: str | None = None
    timeout: int = 120
    max_retries: int = 3


class TokenLimits(BaseModel):
    """Token limit configuration."""

    max_input_tokens: int = 180000
    max_output_tokens: int = 8192
    reserve_for_output: int = 4096


class ModelRouterConfig(BaseModel):
    """Configuration for the model router."""

    default_provider: str = "anthropic"
    default_model: str = "claude-opus-4-5-20251101"
    routes: dict[str, ModelRoute] = Field(default_factory=dict)
    fallbacks: list[ModelRoute] = Field(default_factory=list)
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    token_limits: TokenLimits = Field(default_factory=TokenLimits)


class EmbeddingsConfig(BaseModel):
    """Configuration for embedding generation."""

    provider: str = "sentence_transformers"
    model: str = "BAAI/bge-small-en-v1.5"
    dimension: int = 384
    batch_size: int = 32
    normalize: bool = True
    show_progress: bool = True
    device: str = "cpu"
    query_prefix: str = ""
    cache_folder: str | None = None


class TesseractConfig(BaseModel):
    """Tesseract OCR configuration."""

    lang: str = "eng"
    psm: int = 6
    oem: int = 1
    dpi: int = 300


class OCRThresholds(BaseModel):
    """Thresholds for triggering OCR."""

    min_chars_per_page: int = 200
    min_text_ratio: float = 0.001


class OCRPreprocessing(BaseModel):
    """Image preprocessing settings for OCR."""

    grayscale: bool = True
    threshold: bool = True
    denoise: bool = False
    deskew: bool = True


class OCROutput(BaseModel):
    """OCR output settings."""

    include_confidence: bool = True
    min_confidence: int = 30


class OCRConfig(BaseModel):
    """Configuration for OCR processing."""

    enabled: bool = True
    mode: str = "fallback_only"
    thresholds: OCRThresholds = Field(default_factory=OCRThresholds)
    engine: str = "tesseract"
    tesseract: TesseractConfig = Field(default_factory=TesseractConfig)
    preprocessing: OCRPreprocessing = Field(default_factory=OCRPreprocessing)
    output: OCROutput = Field(default_factory=OCROutput)


class CaseDetectionRule(BaseModel):
    """Rule for detecting case folders."""

    name: str
    pattern: str
    case_type: str


class DocTagRule(BaseModel):
    """Rule for auto-tagging documents."""

    match: str
    tag: str
    priority: int = 5


class ClientFolderConfig(BaseModel):
    """Client folder naming configuration."""

    pattern: str
    fallback_as_name: bool = True


class FolderRulesConfig(BaseModel):
    """Configuration for TaxDome folder parsing."""

    source: str = "taxdome_drive"
    roots: list[str] = Field(default_factory=list)
    client_folder: ClientFolderConfig
    case_detection: list[CaseDetectionRule] = Field(default_factory=list)
    doc_tags: list[DocTagRule] = Field(default_factory=list)
    allowed_extensions: list[str] = Field(default_factory=list)
    ignore_patterns: list[str] = Field(default_factory=list)


class TemplateMetadata(BaseModel):
    """Template metadata from registry.

    Defines template properties including required/optional variables,
    output format, and categorization for discovery.
    """

    id: str
    type: str  # maps to ArtifactType enum
    name: str
    description: str
    filename: str
    variables: dict[str, list[str]] = Field(default_factory=dict)
    output_format: str = "markdown"  # markdown, json, html
    category: str  # communication, intake, correspondence, internal, extraction


class TemplatesConfig(BaseModel):
    """Template registry configuration.

    Contains all template definitions loaded from metadata.yaml.
    Enables dynamic template discovery and validation.
    """

    templates: list[TemplateMetadata] = Field(default_factory=list)
