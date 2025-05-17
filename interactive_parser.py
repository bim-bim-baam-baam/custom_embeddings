from log_storage import LogStorage, LogFile
from log_patterns import LogPatternStore, LogPattern
import re
from typing import Optional, List, Tuple
import sys
import pyperclip

REGEX_PROMPT_TEMPLATE = '''Analyze this log line and create a regex pattern for it:

Log Line: "{line}"

Rules for creating the regex pattern:
1. ONLY use capturing groups () for meaningful message content:
   - DO capture: actual messages, target names, important values
   - DO NOT capture: PIDs, timestamps, technical IDs
   - Regex must start with ^ and and with $.
   
2. The regex MUST contain unique identifiers for the utility:
   - If it's a program log (like userdel, useradd), include the exact program name
   - If it's a build/system message, include the exact unique phrase that identifies this type of message
   
Examples:
1. For log: "<86>May 16 05:13:18 userdel[616177]: delete user 'rooter'"
   Regex: ^<\\d+>\\w{{3}}\\s+\\d{{1,2}}\\s+\\d{{2}}:\\d{{2}}:\\d{{2}}\\s+userdel\\[\\d+\\]:\\s+(.*)$
   Explanation: Only captures the message part, includes 'userdel' as identifier

2. For log: "Building target platforms: x86_64"
   Regex: ^Building target platforms: (\\w+)$
   Explanation: Captures platform name, uses exact phrase "Building target platforms" as identifier

Respond in JSON format with these fields:
{{{{
    "utility_name": "name of the program or unique identifier that generated this log",
    "regex": "regex pattern following the above rules",
}}}}'''

class InteractiveParser:
    def __init__(self):
        self.log_storage = LogStorage("Data/db/logs.db")
        self.pattern_store = LogPatternStore("Data/db/patterns.db")
    
    def get_unprocessed_log(self) -> Optional[LogFile]:
        """Get first unprocessed log file"""
        return self.log_storage.get_random_unprocessed_log()
    
    def parse_line(self, line: str, patterns: List[LogPattern]) -> Optional[LogPattern]:
        """Try to parse a line with existing patterns"""
        for pattern in patterns:
            try:
                if pattern.matches(line):
                    return pattern
            except re.error:
                print(f"Warning: Invalid regex pattern: {pattern.regex}")
        return None
    
    def copy_prompt_to_clipboard(self, line: str):
        """Copy the regex prompt template with the current line to clipboard"""
        prompt = REGEX_PROMPT_TEMPLATE.format(line=line)
        try:
            pyperclip.copy(prompt)
            print("\nPrompt template with current line has been copied to clipboard!")
            print("You can now paste it into your preferred tool.")
        except Exception as e:
            print(f"\nFailed to copy to clipboard: {e}")
            print("\nHere's the prompt to copy manually:")
            print("-" * 80)
            print(prompt)
            print("-" * 80)
    
    def ask_for_new_pattern(self, line: str) -> Tuple[str, str, bool]:
        """Ask user to create a new pattern for unparsed line"""
        print("\nCouldn't parse this line with existing patterns:")
        print(f"Line: {line}")
        
        # Copy prompt to clipboard
        self.copy_prompt_to_clipboard(line)
        
        while True:
            regex = input("\nEnter regex pattern to match this line (or 'q' to quit): ").strip()
            if regex.lower() == 'q':
                return None, None, None
                
            try:
                # Test the regex
                pattern = re.compile(regex)
                # Test if it matches the line
                if not pattern.match(line):
                    print("Warning: This pattern doesn't match the line!")
                    print("Example match attempt:")
                    print(f"Pattern: {regex}")
                    print(f"Line   : {line}")
                    retry = input("Would you like to try another pattern? (y/n): ").lower()
                    if retry == 'y':
                        continue
                    if retry == 'n':
                        if input("Use this non-matching pattern anyway? (y/n): ").lower() != 'y':
                            continue
                
                # Show what groups were captured (if any)
                match = pattern.match(line)
                if match and match.groups():
                    print("\nCapture groups found:")
                    for i, group in enumerate(match.groups(), 1):
                        print(f"Group {i}: {group}")
                    if input("Are these the captures you wanted? (y/n): ").lower() != 'y':
                        continue
                
                break
            except re.error as e:
                print(f"Invalid regex pattern: {e}")
                print("Would you like to:")
                print("1. Try another pattern")
                print("2. See the current line again")
                print("3. Copy prompt to clipboard again")
                print("4. Quit pattern creation")
                choice = input("Choose (1-4): ").strip()
                
                if choice == '2':
                    print(f"\nCurrent line: {line}")
                    continue
                elif choice == '3':
                    self.copy_prompt_to_clipboard(line)
                    continue
                elif choice == '4':
                    return None, None, None
                # For choice 1 or invalid input, continue to next iteration
                continue
        
        utility = input("Enter utility name that produced this line: ").strip()
        
        while True:
            error_str = input("Is this an error line? (y/n): ").strip().lower()
            if error_str in ('y', 'n'):
                break
            print("Please enter 'y' or 'n'")
        
        return regex, utility, error_str == 'y'
    
    def process_log(self, log: LogFile):
        """Process a single log file interactively"""
        print(f"\nProcessing log: {log.packet_name} ({log.architecture})")
        patterns = self.pattern_store.get_all_patterns()
        
        # Split log into lines and process each
        lines = log.log.splitlines()
        total_lines = len(lines)
        
        for i, line in enumerate(lines, 1):
            if not line.strip():  # Skip empty lines
                continue
            
            print(f"\nProcessing line {i}/{total_lines}")
            print(f"Line: {line}")
            
            # Try to match with existing patterns
            matching_pattern = self.parse_line(line, patterns)
            
            if matching_pattern:
                print(f"Matched pattern: {matching_pattern.regex}")
                print(f"Utility: {matching_pattern.utility_name}")
                print(f"Is error: {matching_pattern.is_error}")
            else:
                # Ask user to create new pattern
                if input("\nNo matching pattern found. Create new pattern? (y/n): ").lower() == 'y':
                    regex, utility, is_error = self.ask_for_new_pattern(line)
                    if regex is None:  # User quit pattern creation
                        print("Skipping pattern creation for this line")
                        continue
                    pattern_id = self.pattern_store.add_pattern(regex, utility, is_error)
                    print(f"Added new pattern with ID: {pattern_id}")
                    # Refresh patterns list
                    patterns = self.pattern_store.get_all_patterns()
            
            # Allow user to skip to next file
            if i % 10 == 0:  # Ask every 10 lines
                if input("\nContinue with this file? (y/n): ").lower() != 'y':
                    break
        
        # Mark log as processed
        self.log_storage.mark_as_processed(log.id)
        print(f"\nFinished processing {log.packet_name} and marked as processed")

    def run(self):
        """Main interactive loop"""
        print("Interactive Log Parser")
        print("=====================")
        
        while True:
            log = self.get_unprocessed_log()
            if not log:
                print("\nNo unprocessed logs found!")
                break
            
            self.process_log(log)
            
            if input("\nContinue with next log? (y/n): ").lower() != 'y':
                break
        
        print("\nDone!")

def main():
    parser = InteractiveParser()
    try:
        parser.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)

if __name__ == "__main__":
    main() 