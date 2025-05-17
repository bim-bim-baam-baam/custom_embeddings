from log_patterns import LogPatternStore, LogPattern
import re
import pyperclip
from typing import Optional

REGEX_PROMPT_TEMPLATE = '''Rules for creating the regex pattern:
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
}}}}

For this line: {line}
'''

def parse_line(line: str, patterns: list[LogPattern]) -> Optional[LogPattern]:
    """Try to parse a line with existing patterns"""
    for pattern in patterns:
        try:
            if pattern.matches(line):
                return pattern
        except re.error:
            print(f"Warning: Invalid regex pattern in database: {pattern.regex}")
    return None

def copy_prompt_to_clipboard(line: str):
    """Copy the regex prompt template with the current line to clipboard"""
    prompt = REGEX_PROMPT_TEMPLATE.format(line=line)
    try:
        pyperclip.copy(prompt)
        print("\nPrompt template has been copied to clipboard!")
        print("You can now paste it into your preferred tool.")
    except Exception as e:
        print(f"\nFailed to copy to clipboard: {e}")
        print("\nHere's the prompt to copy manually:")
        print("-" * 80)
        print(prompt)
        print("-" * 80)

def validate_regex(pattern: str, line: str) -> bool:
    """Validate that the regex pattern is valid and matches the line"""
    try:
        # First try to compile the pattern
        compiled = re.compile(pattern)
        
        # Try to match the line
        match = compiled.match(line)
        if not match:
            print("\nWarning: Pattern doesn't match the line!")
            print(f"Pattern: {pattern}")
            print(f"Line   : {line}")
            
            # Show a more detailed comparison
            print("\nPossible issues:")
            if '[' in line and '\\[' not in pattern:
                # Square brackets need to be escaped in regex
                test_pattern = pattern.replace('[', '\\[').replace(']', '\\]')
                try:
                    test_compiled = re.compile(test_pattern)
                    if test_compiled.match(line):
                        print("- Square brackets [] need to be escaped in regex patterns")
                        print(f"- This pattern might work: {test_pattern}")
                except re.error:
                    pass
            
            if pattern.startswith('^') and pattern.endswith('$'):
                # Check if basic character escaping might be the issue
                test_pattern = pattern.replace('\\\\', '\\')
                try:
                    test_compiled = re.compile(test_pattern)
                    if test_compiled.match(line):
                        print("- Double backslashes detected. Try using single backslashes for escaping.")
                        print(f"- This pattern might work: {test_pattern}")
                except re.error:
                    pass
            else:
                print("- Pattern should start with '^' and end with '$' to match the entire line")
            
            # Try to create a working pattern from the line
            suggested_pattern = '^' + re.escape(line) + '$'
            try:
                test_compiled = re.compile(suggested_pattern)
                if test_compiled.match(line):
                    print("\nSuggested pattern (exact match):")
                    print(suggested_pattern)
                    print("\nYou can modify this pattern to make it more general by:")
                    print("1. Replacing specific numbers with \\d+")
                    print("2. Replacing specific words with .* where appropriate")
                    print("3. Adding capture groups () around important parts")
            except re.error:
                pass
            
            return False
        
        # Show captured groups if any
        if match.groups():
            print("\nCapture groups found:")
            for i, group in enumerate(match.groups(), 1):
                print(f"Group {i}: {group}")
        
        return True
    except re.error as e:
        print(f"\nInvalid regex pattern: {e}")
        return False

def main():
    pattern_store = LogPatternStore("Data/db/patterns.db")
    
    try:
        while True:
            print("\nEnter a log line to process (Ctrl+C to exit):")
            print("-" * 50)
            
            # Get the log line
            line = input("Log line: ").strip()
            if not line:
                print("Log line cannot be empty")
                continue
            
            # Try to match with existing patterns
            patterns = pattern_store.get_all_patterns()
            matching_pattern = parse_line(line, patterns)
            
            if matching_pattern:
                print("\nFound matching pattern:")
                print(f"Pattern ID: {matching_pattern.id}")
                print(f"Regex: {matching_pattern.regex}")
                print(f"Utility: {matching_pattern.utility_name}")
                print(f"Is error: {matching_pattern.is_error}")
                
                action = input("\nWhat would you like to do? (k)eep pattern, (d)elete pattern: ").lower().strip()
                if action == 'd':
                    pattern_store.delete_pattern(matching_pattern.id)
                    print(f"Pattern {matching_pattern.id} deleted.")
                continue
            
            print("\nNo matching pattern found.")
            if input("Would you like to create a new pattern? (y/n): ").lower() != 'y':
                continue
            
            # Copy prompt to clipboard with the current line
            copy_prompt_to_clipboard(line)
            
            # Get and validate the regex pattern
            while True:
                regex = input("\nRegex pattern: ").strip()
                if not regex:
                    print("Regex pattern cannot be empty")
                    continue
                
                if validate_regex(regex, line):
                    break
                
                print("\nWould you like to:")
                print("1. Try another pattern")
                print("2. Copy prompt to clipboard again")
                print("3. Cancel pattern creation")
                choice = input("Choose (1-3): ").strip()
                
                if choice == '2':
                    copy_prompt_to_clipboard(line)
                    continue
                elif choice == '3':
                    print("Pattern creation cancelled")
                    break
                # For choice 1 or invalid input, continue to next iteration
                continue
            
            if not regex:
                continue
            
            # Get utility name
            utility = input("Utility name: ").strip()
            if not utility:
                print("Utility name cannot be empty")
                continue
            
            # Get error status
            while True:
                error_str = input("Is this an error line? (y/n): ").strip().lower()
                if error_str in ('y', 'n'):
                    break
                print("Please enter 'y' or 'n'")
            
            # Add the pattern
            pattern_id = pattern_store.add_pattern(regex, utility, error_str == 'y')
            print(f"\nSuccessfully added pattern with ID: {pattern_id}")
        
    except KeyboardInterrupt:
        print("\nProgram terminated")

if __name__ == "__main__":
    main() 