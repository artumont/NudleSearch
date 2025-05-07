import os
import logging
import sqlite3

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        try:
            self.conn = sqlite3.connect(os.environ.get("DATABASE_PATH"))
            if self.ensure_structure():
                logger.error("Database structure not created. Exiting.")
                exit(1)
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")

    def ensure_structure(self) -> None | Exception:
        try:
            cursor = self.conn.cursor()

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
                    positions TEXT,  -- Stored as comma-separated positions
                    FOREIGN KEY (keyword_id) REFERENCES keywords (keyword_id),
                    FOREIGN KEY (doc_id) REFERENCES documents (doc_id),
                    PRIMARY KEY (keyword_id, doc_id)
                )
            """)

            # @note: Create indexes for faster searches
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_url ON documents(url)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_word ON keywords(word)")

            self.conn.commit()
            return None
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            return e
