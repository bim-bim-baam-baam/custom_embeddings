import os
from pathlib import Path
import re
from typing import List, Tuple, Set

# Error keywords to look for
ERROR_KEYWORDS = [
    r'\berror\b',
    r'\bfailed\b',
    r'\bfailure\b',
    r'\bfatal\b',
    r'\berror:',
    r'\bfailed:',
    r'\bfailure:',
    r'\bfatal:',
    r'\bundefined reference\b',
    r'\bcannot find\b',
    r'\bnot found\b',
    r'\bcompilation failed\b',
    r'\bcommand failed\b',
    r'make: \*\*\* \[',
    r'\bsegmentation fault\b',
    r'\bassertion failed\b',
    r'\bpermission denied\b',
    r'\bno such file\b',
    r'\bsyntax error\b',
    r'\blinker error\b',
    r'\bmissing\b',
    r'\brequired by\b',
    r'\bconflicts\b'
]

# Compile patterns once for efficiency
ERROR_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in ERROR_KEYWORDS]

def find_error_windows(lines: List[str], window_size: int = 2) -> Set[int]:
    """Find all line numbers that should be included in error windows"""
    line_numbers = set()
    
    for i, line in enumerate(lines):
        line = line.strip()
        # Skip lines that:
        # - start with '+'
        # - contain 'warning'
        # - start with 'checking' and end with 'yes'
        if (line.startswith('+') or 
            re.search(r'\bwarning\b', line, re.IGNORECASE) or
            (line.lower().startswith('checking') and line.lower().rstrip().endswith('yes'))):
            continue
            
        # Check for error keywords using word boundaries
        if any(pattern.search(line) for pattern in ERROR_PATTERNS):
            # Add the window range to the set
            start = max(0, i - window_size)
            end = min(len(lines), i + window_size + 1)
            line_numbers.update(range(start, end))
    
    return line_numbers

def process_log_file(input_path, output_dir):
    """Process a single log file and extract unique error windows"""
    try:
        # Read the log file
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find all lines that should be included
        line_numbers = find_error_windows(lines)
        
        if not line_numbers:
            return False
        
        # Create output path preserving the original filename
        output_path = output_dir / input_path.name
        
        # Save only the unique lines in order
        with open(output_path, 'w', encoding='utf-8') as f:
            for i in sorted(line_numbers):
                f.write(lines[i])
        
        return True
        
    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        return False

def main():
    # Setup directories
    input_dir = Path("Data/x86_64/error")
    output_dir = Path("Data/x86_64/error_processed")
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process all log files
    for root, _, files in os.walk(input_dir):
        root_path = Path(root)
        for file in files:
            input_path = root_path / file
            process_log_file(input_path, output_dir)

if __name__ == "__main__":
    main() 