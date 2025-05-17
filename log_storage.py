import sqlite3
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import os

@dataclass
class LogFile:
    id: int
    packet_name: str
    architecture: str
    date: str
    error: bool
    log: str
    processed: bool

class LogStorage:
    def __init__(self, db_path: str = "Data/db/error_logs.db"):
        self.db_path = Path(db_path)
        # Ensure the directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY,
                    packet_name TEXT NOT NULL,
                    architecture TEXT NOT NULL,
                    date TEXT NOT NULL,
                    error BOOLEAN NOT NULL,
                    log TEXT NOT NULL,
                    processed BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)
    
    def add_log(self, packet_name: str, architecture: str, date: str, 
                error: bool, log: str, processed: bool = False) -> int:
        """Add a new log entry and return its ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO logs 
                   (packet_name, architecture, date, error, log, processed) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (packet_name, architecture, date, error, log, processed)
            )
            return cursor.lastrowid
    
    def get_log(self, log_id: int) -> Optional[LogFile]:
        """Get a log by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM logs WHERE id = ?", (log_id,))
            row = cursor.fetchone()
            if row:
                return LogFile(row[0], row[1], row[2], row[3], bool(row[4]), row[5], bool(row[6]))
            return None
    
    def get_all_logs(self) -> list[LogFile]:
        """Get all logs"""
        logs = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM logs")
            for row in cursor:
                logs.append(LogFile(row[0], row[1], row[2], row[3], bool(row[4]), row[5], bool(row[6])))
        return logs

    def import_from_data_dir(self, data_dir: str = "Data"):
        """Import all logs from the Data directory"""
        data_path = Path(data_dir)
        if not data_path.exists():
            print(f"Directory {data_dir} does not exist")
            return
        
        # Iterate through architecture directories (x86_64, i586)
        for arch_dir in data_path.iterdir():
            if not arch_dir.is_dir():
                continue
                
            architecture = arch_dir.name  # x86_64 or i586
            
            # Iterate through result directories (success, error)
            for result_dir in arch_dir.iterdir():
                if not result_dir.is_dir():
                    continue
                    
                # Determine if this is an error or success based on directory name
                is_error = result_dir.name.lower() == "error_processed"

                if not is_error:
                    continue
                
                # Process all files in this directory
                for file_path in result_dir.iterdir():
                    if not file_path.is_file():
                        continue
                        
                    try:
                        # Extract packet name from filename
                        packet_name = file_path.name
                        
                        # Read log content
                        with open(file_path, 'r', encoding='utf-8') as f:
                            log_content = f.read()
                        
                        # Use file modification time as date
                        date = file_path.stat().st_mtime
                        
                        # Add to database
                        self.add_log(
                            packet_name=packet_name,
                            architecture=architecture,
                            date=str(date),
                            error=is_error,
                            log=log_content,
                            processed=False
                        )
                        print(f"Imported {packet_name} ({architecture}, {'error' if is_error else 'success'})")
                    except Exception as e:
                        print(f"Error importing {file_path}: {str(e)}")

    def mark_as_processed(self, log_id: int):
        """Mark a log as processed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE logs SET processed = TRUE WHERE id = ?", (log_id,))
            conn.commit()

    def get_first_unprocessed_log(self) -> Optional[LogFile]:
        """Get the first unprocessed log from the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM logs WHERE processed = FALSE LIMIT 1")
            row = cursor.fetchone()
            if row:
                return LogFile(row[0], row[1], row[2], row[3], bool(row[4]), row[5], bool(row[6]))
            return None

    def get_random_unprocessed_log(self, limit: int = 30) -> Optional[LogFile]:
        """Get a random unprocessed log from the database"""
        with sqlite3.connect(self.db_path) as conn:
            # First get up to 'limit' random unprocessed logs
            cursor = conn.execute(
                "SELECT * FROM logs WHERE processed = FALSE ORDER BY RANDOM() LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            if not rows:
                return None
                
            # Return one random log from the subset
            row = rows[0]  # Since we already randomized with ORDER BY RANDOM()
            return LogFile(row[0], row[1], row[2], row[3], bool(row[4]), row[5], bool(row[6]))

def main():
    # Example usage
    storage = LogStorage()
    
    # Import logs from Data directory
    print("Importing logs from Data directory...")
    storage.import_from_data_dir()
    
    # Print summary
    logs = storage.get_all_logs()
    print(f"\nImported {len(logs)} logs:")
    for log in logs:
        print(f"- {log.packet_name} ({log.architecture}, {'error' if log.error else 'success'})")

if __name__ == "__main__":
    main() 