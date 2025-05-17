import sqlite3
import re
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class LogPattern:
    id: int
    regex: str
    utility_name: str
    is_error: bool
    need_reviewing: bool = True  # Default to True for new patterns
    
    def matches(self, line: str) -> bool:
        """Test if this pattern matches a given line"""
        try:
            return bool(re.match(self.regex, line))
        except re.error:
            return False

class LogPatternStore:
    def __init__(self, db_path: str = "Data/db/patterns.db"):
        self.db_path = Path(db_path)
        # Ensure the directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            # First check if need_reviewing column exists
            cursor = conn.execute("PRAGMA table_info(patterns)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if "patterns" not in columns:
                # Create new table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS patterns (
                        id INTEGER PRIMARY KEY,
                        regex TEXT NOT NULL,
                        utility_name TEXT NOT NULL,
                        is_error BOOLEAN NOT NULL,
                        need_reviewing BOOLEAN NOT NULL DEFAULT TRUE
                    )
                """)
            elif "need_reviewing" not in columns:
                # Add column to existing table
                conn.execute("ALTER TABLE patterns ADD COLUMN need_reviewing BOOLEAN NOT NULL DEFAULT TRUE")
    
    def add_pattern(self, regex: str, utility_name: str, is_error: bool, need_reviewing: bool = True) -> int:
        """Add a new pattern and return its ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO patterns (regex, utility_name, is_error, need_reviewing) VALUES (?, ?, ?, ?)",
                (regex, utility_name, is_error, need_reviewing)
            )
            return cursor.lastrowid
    
    def get_pattern(self, pattern_id: int) -> Optional[LogPattern]:
        """Get a pattern by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM patterns WHERE id = ?", (pattern_id,))
            row = cursor.fetchone()
            if row:
                return LogPattern(row[0], row[1], row[2], bool(row[3]), bool(row[4]))
            return None
    
    def get_all_patterns(self) -> list[LogPattern]:
        """Get all patterns"""
        patterns = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM patterns")
            for row in cursor:
                patterns.append(LogPattern(row[0], row[1], row[2], bool(row[3]), bool(row[4])))
        return patterns

    def mark_reviewed(self, pattern_id: int):
        """Mark a pattern as reviewed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE patterns SET need_reviewing = FALSE WHERE id = ?", (pattern_id,))
            conn.commit()

    def delete_pattern(self, pattern_id: int) -> bool:
        """Delete a pattern by ID. Returns True if pattern was deleted, False if pattern was not found."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM patterns WHERE id = ?", (pattern_id,))
            conn.commit()
            return cursor.rowcount > 0

def main():
    # Example usage
    store = LogPatternStore()
    
    # Example patterns
    example_patterns = [
        ("\\[ERROR\\].*", "generic", True),
        ("make\\[\\d+\\]:.*Error\\s+\\d+", "make", True),
        ("\\[INFO\\].*", "generic", False),
        ("gcc:.*error:.*", "gcc", True),
        ("CMake Error.*", "cmake", True),
        ("npm ERR!.*", "npm", True),
        ("warning:.*", "generic", False),
        ("\\[WARNING\\].*", "generic", False),
        ("python.*Traceback.*", "python", True),
        ("Segmentation fault.*", "generic", True)
    ]
    
    # Add example patterns
    for regex, utility, is_error in example_patterns:
        pattern_id = store.add_pattern(regex, utility, is_error)
        print(f"Added pattern {pattern_id}: {regex} for {utility} (error: {is_error})")

if __name__ == "__main__":
    main() 