import logging
import sqlite3
from datetime import datetime
from typing import Any, Generator
from contextlib import contextmanager
from nudlecrawler.database.exceptions import SQLiteConnectionException, SQLiteSchemaException

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for the web crawler.

    This class handles all database interactions including connection management,
    schema initialization, and transaction handling. It ensures thread-safe
    database operations through context managers.

    Attributes:
        filepath (str): Path to the SQLite database file.
        connection (sqlite3.Connection | None): Active SQLite database connection.
    """

    def __init__(self, filepath: str):
        """Initialize SQLite database handler.

        This constructor initializes the database connection and ensures proper table schema.

        Args:
            filepath (str): Path to the SQLite database file.

        Attributes:
            filepath (str): Stored path to the database file.
            connection (sqlite3.Connection | None): Database connection object, None if not connected.
        """
        self.filepath: str = filepath
        self.connection: sqlite3.Connection | None = None

        self._connect()
        self._ensure_schema()

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit method for context manager.

        This method is called when exiting the context manager. It ensures that
        the database connection is closed properly.
        """
        self.close()

    # @context: Utilities
    def close(self) -> None:
        """Close the database connection.

        This method closes the SQLite database connection if it is open.
        It should be called when the database operations are complete to free up resources.
        """
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed.")
        else:
            logger.warning("No active database connection to close.")

    # @context: Public

    # @context: Private
    def _connect(self) -> bool:
        """Establish a connection to the SQLite database.

        Initializes the database connection with support for custom column types
        and enables foreign key constraints.

        Returns:
            bool: True if connection is successful.

        Raises:
            sqlite3.Error: If connection to the database fails.
        """
        try:
            self.connection = sqlite3.connect(
                self.filepath,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            self.connection.execute("PRAGMA foreign_keys = ON")
            logger.info("Connected to the database.")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to the database: {e}")
            return False

    def _ensure_schema(self) -> None:
        """Initialize or validate the database schema.

        Creates the following tables if they don't exist:
        - documents: Stores webpage data (URL, title, content)
        - keywords: Stores unique keywords found in documents
        - inverted_index: Maps keywords to their occurrences in documents

        Also creates necessary indices for optimized queries.

        Raises:
            sqlite3.Error: If schema creation or validation fails.
        """
        try:
            with self._transaction() as cursor:
                logger.info("Ensuring database schema...")

                # @note: Documents table - stores webpage information
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT UNIQUE NOT NULL,
                        title TEXT,
                        content TEXT,
                        last_crawl TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )                  
                """)

                # @note: Keywords table - stores keywords for documents
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS keywords (
                        keyword_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        word TEXT UNIQUE NOT NULL
                    )
                """)

                # @note: Inverted index table - stores keyword positions in documents
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS inverted_index (
                        keyword_id INTEGER,
                        doc_id INTEGER,
                        frequency INTEGER,
                        positions TEXT,  -- # @note: Stored as comma-separated positions
                        FOREIGN KEY (keyword_id) REFERENCES keywords (keyword_id),
                        FOREIGN KEY (doc_id) REFERENCES documents (doc_id),
                        PRIMARY KEY (keyword_id, doc_id)
                    )
                """)

                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_url ON documents(url)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_word ON keywords(word)")

            logger.info("Database schema ensured.")
        except sqlite3.Error as e:
            logger.error(f"Failed to ensure database schema: {e}")
            raise SQLiteSchemaException(
                f"Failed to ensure database schema: {e}")

    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """Provide a transactional context for database operations.

        Creates a new cursor and manages the transaction lifecycle including
        commit on success and rollback on failure. Ensures proper resource cleanup.

        Yields:
            sqlite3.Cursor: Database cursor for executing SQL commands.

        Raises:
            SQLiteConnectionException: If database connection cannot be established or is invalid
            sqlite3.Error: If any database operation within the transaction fails
        """
        if not self.connection and not self._connect():
            raise SQLiteConnectionException(
                "Failed to establish database connection")

        if not isinstance(self.connection, sqlite3.Connection):
            raise SQLiteConnectionException(
                "Invalid database connection state")

        cursor = self.connection.cursor()
        try:
            yield cursor
            if self.connection:
                self.connection.commit()
        except sqlite3.Error as e:
            if self.connection:
                self.connection.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
