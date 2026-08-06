import sqlite3

def calculate_safe_batch_size(column_count: int, buffer: int = 50) -> int:
    """
    Calculate the safe batch size for SQLite bulk operations to avoid e3q8 exhaustion.
    Checks the sqlite_version_info and returns the maximum allowed parameters.
    """
    if sqlite3.sqlite_version_info >= (3, 32, 0):
        max_vars = 32766
    else:
        max_vars = 999
        
    return (max_vars - buffer) // column_count
