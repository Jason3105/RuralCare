"""
Database utility functions to handle connection issues
"""
from django.db import connection
from django.core.exceptions import ImproperlyConfigured
import logging

logger = logging.getLogger(__name__)


def close_old_connections():
    """
    Close any stale database connections.
    This helps prevent cursor errors when connections are lost.
    """
    try:
        connection.close()
    except Exception as e:
        logger.warning(f"Error closing database connection: {e}")


def ensure_db_connection():
    """
    Ensure database connection is active.
    If connection is closed, it will be reopened automatically.
    """
    try:
        # Test connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        # Close and let Django reopen
        close_old_connections()
        return False
