class SQLiteConnectionException(Exception):
    """Exception raised when the SQLite connection fails."""
    pass

class SQLiteSchemaException(Exception):
    """Exception raised when the SQLite schema is invalid."""
    pass