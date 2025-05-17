from typing import Optional, List, Tuple
from dataclasses import dataclass
from log_storage import LogFile, LogStorage
from log_patterns import LogPattern, LogPatternStore

@dataclass
class ParseResult:
    is_parsable: bool
    utility_name: Optional[str] = None
    error_type: Optional[str] = None
    confidence: float = 0.0

class LogAPI:
    def __init__(self, log_db: str = "logs.db", pattern_db: str = "patterns.db"):
        self.log_storage = LogStorage(log_db)
        self.pattern_store = LogPatternStore(pattern_db)
    
    def get_all_logs(self) -> List[LogFile]:
        """Get all logs from the database"""
        return self.log_storage.get_all_logs()
    
    def get_unprocessed_logs(self) -> List[LogFile]:
        """Get all unprocessed logs"""
        return [log for log in self.get_all_logs() if not log.processed]
    
    def check_line_parsable(self, line: str) -> ParseResult:
        """
        Check if a line can be parsed by any of our patterns
        Returns ParseResult with parsing information
        """
        # This is just a signature - implementation will be in parser.py
        raise NotImplementedError("Implementation will be in parser.py")
    
    def parse_log_file(self, log_file: LogFile) -> List[Tuple[str, ParseResult]]:
        """
        Parse an entire log file and return list of (line, parse_result) tuples
        Returns list of tuples containing the line and its parse result
        """
        # This is just a signature - implementation will be in parser.py
        raise NotImplementedError("Implementation will be in parser.py")
    
    def mark_log_as_processed(self, log_id: int):
        """Mark a log as processed in the database"""
        # This is just a signature - implementation will be in parser.py
        raise NotImplementedError("Implementation will be in parser.py")

def main():
    # Example usage
    api = LogAPI()
    
    # Get all logs
    all_logs = api.get_all_logs()
    print(f"Total logs in database: {len(all_logs)}")
    
    # Get unprocessed logs
    unprocessed = api.get_unprocessed_logs()
    print(f"Unprocessed logs: {len(unprocessed)}")
    
    # Example of checking a line (this would raise NotImplementedError)
    try:
        result = api.check_line_parsable("[ERROR] Failed to compile")
        print(f"Parse result: {result}")
    except NotImplementedError:
        print("Parser not yet implemented")

if __name__ == "__main__":
    main() 