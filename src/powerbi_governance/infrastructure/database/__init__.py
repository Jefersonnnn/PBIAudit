"""
Database initialization and session management
"""

from typing import Generator

import structlog
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from powerbi_governance.core import Settings, get_settings

log = structlog.get_logger(__name__)


class DatabaseManager:
    """
    Manages database connections and sessions.
    
    Provides factory for creating database sessions with proper
    configuration and lifecycle management.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize database manager.
        
        Args:
            settings: Application settings (uses get_settings() if None)
        """
        self.settings = settings or get_settings()
        self.engine = None
        self.session_factory = None

    def initialize(self) -> None:
        """
        Initialize database engine and session factory.
        
        Creates connection pool and configures SQLAlchemy for the application.
        """
        try:
            log.info("Initializing database connection", database_url=str(self.settings.database_url).split("@")[0])

            # Create engine with connection pooling
            self.engine = create_engine(
                str(self.settings.database_url),
                pool_size=self.settings.database_pool_size,
                max_overflow=self.settings.database_max_overflow,
                pool_recycle=self.settings.database_pool_recycle,
                echo=self.settings.database_echo,
                future=True,
            )

            # Configure connection event logging
            if self.settings.debug:
                @event.listens_for(self.engine, "before_cursor_execute")
                def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
                    log.debug("SQL statement", sql=statement[:100])

            # Create session factory
            self.session_factory = sessionmaker(
                bind=self.engine,
                class_=Session,
                expire_on_commit=False,
                future=True,
            )

            log.info("Database connection initialized successfully")

        except Exception as e:
            log.error("Failed to initialize database", error=str(e))
            raise

    def get_session(self) -> Session:
        """
        Get a new database session.
        
        Returns:
            SQLAlchemy Session instance
            
        Raises:
            RuntimeError: If database not initialized
        """
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return self.session_factory()

    def close(self) -> None:
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            log.info("Database connections closed")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection generator for database sessions.
    
    Yields a session and ensures proper cleanup.
    
    Usage:
        >>> session: Session = next(get_db())
        
    Yields:
        SQLAlchemy Session
    """
    db_manager = DatabaseManager()
    db_manager.initialize()
    session = db_manager.get_session()

    try:
        yield session
    finally:
        session.close()


__all__ = [
    "DatabaseManager",
    "get_db",
]
