"""
Main application entry point
"""

import asyncio

import structlog

from powerbi_governance.core import configure_logging, get_settings

log = structlog.get_logger(__name__)


async def main() -> None:
    """
    Main application entry point.
    
    Initializes configuration, logging and core services.
    """
    # Get settings
    settings = get_settings()

    # Configure logging
    configure_logging(settings)

    log.info(
        "PowerBI Governance Platform started",
        environment=settings.environment,
        version="0.1.0",
    )

    try:
        # TODO: Initialize services and start background jobs
        log.info("Application initialized successfully")

    except Exception as e:
        log.error("Application initialization failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
