"""NAS Sync Agent entry point.

CLI tool for monitoring and syncing files from the NAS to Le CPA Agent.

Commands:
    watch   - Start filesystem watcher for real-time sync
    scan    - Perform full scan of NAS for initial backfill
    digest  - Send the daily digest email manually
"""

import asyncio
import signal
from pathlib import Path

import structlog
import typer
import yaml

from nas_sync.config import get_default_config, load_config

app = typer.Typer(
    name="nas-sync",
    help="NAS filesystem sync agent for Le CPA Agent",
    add_completion=False,
)


def setup_logging(level: str = "INFO", log_format: str = "json") -> None:
    """Configure structured logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_format: Output format ("json" or "console")
    """
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


@app.command()
def watch(
    config_path: Path = typer.Option(
        Path("config.yaml"),
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """Start the filesystem watcher for real-time sync.

    Monitors the NAS directory and sends file notifications to the API
    as changes occur. Runs until interrupted with Ctrl+C.
    """
    from nas_sync.watcher import NASWatcher

    config = load_config(config_path)
    setup_logging(config.logging.level, config.logging.format)

    logger = structlog.get_logger()
    logger.info("Starting NAS watcher", config=str(config_path))

    watcher = NASWatcher(config)

    # Setup signal handlers
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown(sig: signal.Signals) -> None:
        logger.info("Received shutdown signal", signal=sig.name)
        watcher.stop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown, sig)

    try:
        watcher.start()
        loop.run_until_complete(watcher.run_processing_loop())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        watcher.stop()
    finally:
        loop.close()


@app.command()
def scan(
    config_path: Path = typer.Option(
        Path("config.yaml"),
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    client_filter: str = typer.Option(
        None,
        "--clients",
        help="Comma-separated list of client codes to process",
    ),
    year_filter: str = typer.Option(
        None,
        "--years",
        help="Comma-separated list of years to process",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Don't actually send notifications, just count files",
    ),
) -> None:
    """Run a full scan of the NAS for initial backfill.

    Walks the entire NAS directory structure and sends notifications
    for all existing files. Use filters to process specific clients
    or years.

    Examples:
        nas-sync scan --dry-run
        nas-sync scan --clients 1001,1002 --years 2024,2023
    """
    from nas_sync.scanner import FullScanner

    config = load_config(config_path)
    setup_logging(config.logging.level, config.logging.format)

    logger = structlog.get_logger()
    logger.info("Starting full scan", config=str(config_path), dry_run=dry_run)

    scanner = FullScanner(config)

    # Parse filters
    clients = client_filter.split(",") if client_filter else None
    years = [int(y.strip()) for y in year_filter.split(",")] if year_filter else None

    results = asyncio.run(
        scanner.scan(
            client_filter=clients,
            year_filter=years,
            dry_run=dry_run,
        )
    )

    # Print results
    typer.echo("\n--- Scan Results ---")
    typer.echo(f"Files scanned:  {results['files_scanned']}")
    typer.echo(f"Files queued:   {results['files_queued']}")
    typer.echo(f"Files skipped:  {results['files_skipped']}")
    typer.echo(f"Files failed:   {results['files_failed']}")
    typer.echo(f"Relationships:  {results['relationships_found']}")

    if dry_run:
        typer.echo("\n(Dry run - no notifications sent)")


@app.command()
def digest(
    config_path: Path = typer.Option(
        Path("config.yaml"),
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """Send the daily digest email manually.

    Generates and sends the sync status digest email to configured
    recipients. Normally this is triggered automatically by a scheduler.
    """
    from nas_sync.digest import DigestSender

    config = load_config(config_path)
    setup_logging(config.logging.level, config.logging.format)

    logger = structlog.get_logger()
    logger.info("Sending digest email")

    sender = DigestSender(config)
    asyncio.run(sender.send())

    typer.echo("Digest email sent")


@app.command()
def init_config(
    output_path: Path = typer.Option(
        Path("config.yaml"),
        "--output",
        "-o",
        help="Path to write configuration file",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing file",
    ),
) -> None:
    """Generate a default configuration file.

    Creates a config.yaml file with default settings that you can
    customize for your environment.
    """
    if output_path.exists() and not force:
        typer.echo(f"File already exists: {output_path}")
        typer.echo("Use --force to overwrite")
        raise typer.Exit(1)

    default_config = get_default_config()

    with open(output_path, "w") as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

    typer.echo(f"Configuration written to: {output_path}")
    typer.echo("Edit the file to customize settings for your environment.")


@app.command()
def validate(
    config_path: Path = typer.Option(
        Path("config.yaml"),
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """Validate the configuration file.

    Checks that the configuration file is valid and all required
    settings are present.
    """
    try:
        config = load_config(config_path)
        typer.echo("Configuration is valid")
        typer.echo(f"  NAS root: {config.nas.root_path}")
        typer.echo(f"  API base URL: {config.api.base_url}")
        typer.echo(f"  Client patterns: {len(config.parsing.client_patterns)}")
        typer.echo(f"  Skip patterns: {len(config.parsing.skip_patterns)}")
        typer.echo(f"  Document tag patterns: {len(config.parsing.document_tags)}")
    except FileNotFoundError as e:
        typer.echo(f"Configuration file not found: {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        typer.echo(f"Configuration error: {e}")
        raise typer.Exit(1) from None


if __name__ == "__main__":
    app()
