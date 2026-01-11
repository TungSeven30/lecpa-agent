"""Template rendering service using Jinja2.

Provides centralized template discovery, validation, and rendering for all agents.
Custom filters support currency formatting and SSN masking for CPA-specific use cases.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import structlog
from jinja2 import (
    Environment,
    FileSystemLoader,
    TemplateNotFound,
    select_autoescape,
)

from shared.config.loader import load_templates_config
from shared.config.schemas import TemplateMetadata, TemplatesConfig

logger = structlog.get_logger()


class TemplateRenderer:
    """Service for rendering Jinja2 templates with validation.

    Features:
    - Template discovery from metadata registry
    - Variable validation against schema
    - Custom filters (currency, SSN masking)
    - Error handling for missing variables

    Example:
        renderer = get_template_renderer()
        rendered = renderer.render(
            "missing_docs_email",
            {"client_name": "John Doe", "tax_year": "2024", ...}
        )
    """

    def __init__(self, templates_dir: Path) -> None:
        """Initialize the template renderer.

        Args:
            templates_dir: Path to templates directory

        Raises:
            FileNotFoundError: If templates directory doesn't exist
        """
        if not templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

        self.templates_dir = templates_dir
        self.config = load_templates_config()

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters for CPA-specific formatting
        self.env.filters["format_currency"] = self._format_currency
        self.env.filters["mask_ssn"] = self._mask_ssn

        logger.info(
            "Template renderer initialized",
            templates_count=len(self.config.templates),
            templates_dir=str(templates_dir),
        )

    def get_template_metadata(self, template_id: str) -> TemplateMetadata | None:
        """Get template metadata by ID.

        Args:
            template_id: Template identifier

        Returns:
            Template metadata or None if not found
        """
        for template in self.config.templates:
            if template.id == template_id:
                return template
        return None

    def list_templates(
        self,
        template_type: str | None = None,
        category: str | None = None,
    ) -> list[TemplateMetadata]:
        """List available templates with optional filtering.

        Args:
            template_type: Filter by artifact type (e.g., "missing_docs_email")
            category: Filter by category (e.g., "communication")

        Returns:
            List of template metadata matching filters
        """
        templates = self.config.templates

        if template_type:
            templates = [t for t in templates if t.type == template_type]

        if category:
            templates = [t for t in templates if t.category == category]

        return templates

    def validate_variables(
        self,
        template_id: str,
        variables: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate variables against template schema.

        Args:
            template_id: Template identifier
            variables: Template variables to validate

        Returns:
            Tuple of (is_valid, missing_required_vars)
        """
        metadata = self.get_template_metadata(template_id)
        if not metadata:
            return False, [f"Template not found: {template_id}"]

        required_vars = metadata.variables.get("required", [])
        missing = [var for var in required_vars if var not in variables]

        return len(missing) == 0, missing

    def render(
        self,
        template_id: str,
        variables: dict[str, Any],
        validate: bool = True,
    ) -> str:
        """Render a template with variables.

        Args:
            template_id: Template identifier (e.g., "missing_docs_email")
            variables: Template variables as dict
            validate: Whether to validate variables before rendering

        Returns:
            Rendered template content

        Raises:
            ValueError: If template not found or variables invalid
            TemplateNotFound: If template file not found on disk
        """
        metadata = self.get_template_metadata(template_id)
        if not metadata:
            raise ValueError(f"Template not found: {template_id}")

        # Validate required variables if requested
        if validate:
            is_valid, missing = self.validate_variables(template_id, variables)
            if not is_valid:
                raise ValueError(
                    f"Missing required variables for template '{template_id}': "
                    f"{', '.join(missing)}"
                )

        try:
            template = self.env.get_template(metadata.filename)
            rendered = template.render(**variables)

            logger.info(
                "Template rendered successfully",
                template_id=template_id,
                output_length=len(rendered),
                variables_count=len(variables),
            )

            return rendered

        except TemplateNotFound as e:
            logger.error(
                "Template file not found",
                template_id=template_id,
                filename=metadata.filename,
            )
            raise ValueError(
                f"Template file not found: {metadata.filename}"
            ) from e

    @staticmethod
    def _format_currency(value: float | int | str) -> str:
        """Format value as US currency.

        Args:
            value: Numeric value to format

        Returns:
            Formatted currency string (e.g., "$1,234.56")
        """
        try:
            numeric_value = float(value)
            return f"${numeric_value:,.2f}"
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _mask_ssn(ssn: str) -> str:
        """Mask SSN showing only last 4 digits.

        Args:
            ssn: Social Security Number (any format)

        Returns:
            Masked SSN (e.g., "XXX-XX-1234")
        """
        if not ssn:
            return "XXX-XX-XXXX"

        # Extract only digits
        digits = "".join(c for c in str(ssn) if c.isdigit())

        if len(digits) < 4:
            return "XXX-XX-XXXX"

        return f"XXX-XX-{digits[-4:]}"


@lru_cache
def get_template_renderer() -> TemplateRenderer:
    """Get cached template renderer instance.

    Returns:
        Singleton TemplateRenderer instance

    Raises:
        FileNotFoundError: If templates directory not found
    """
    # Find templates directory relative to project root
    current_file = Path(__file__).resolve()
    for parent in current_file.parents:
        templates_dir = parent / "config" / "templates"
        if templates_dir.is_dir():
            return TemplateRenderer(templates_dir)

    raise FileNotFoundError("Templates directory not found in project")
