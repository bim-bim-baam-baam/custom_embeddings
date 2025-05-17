from log_storage import LogStorage, LogFile
from log_patterns import LogPatternStore, LogPattern
import re
from typing import Optional, Tuple, List
from dataclasses import dataclass
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_URL = "https://api.intelligence.io.solutions/api/v1/chat/completions"
AI_MODEL = "deepseek-ai/DeepSeek-R1"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

@dataclass
class ParsedLine:
    utility_name: str
    message: str
    is_error: bool
    error_reason: Optional[str] = None

class LLMParser:
    def __init__(self):
        self.log_storage = LogStorage("Data/db/logs.db")
        self.pattern_store = LogPatternStore("Data/db/patterns.db")
        self._patterns = None
    
    @property
    def patterns(self):
        """Cached access to patterns"""
        if self._patterns is None:
            self._patterns = self.pattern_store.get_all_patterns()
        return self._patterns
    
    def _update_patterns(self, regex: str, utility_name: str, is_error: bool):
        """Update both DB and cache when adding a new pattern"""
        # Add pattern with need_reviewing=True since it's LLM-generated
        pattern_id = self.pattern_store.add_pattern(regex, utility_name, is_error, need_reviewing=True)
        
        # Create pattern object with the new ID
        new_pattern = LogPattern(id=pattern_id, regex=regex, utility_name=utility_name, is_error=is_error, need_reviewing=True)
        
        # Update cache if it exists
        if self._patterns is not None:
            self._patterns.append(new_pattern)
            
        return pattern_id

    def ask_llm(self, prompt: str) -> str:
        """Ask LLM a question and get response using direct API call"""
        try:
            data = {
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a log analysis expert. Think through each step carefully before responding."},
                    {"role": "user", "content": prompt}
                ]
            }
            
            response = requests.post(API_URL, headers=HEADERS, json=data)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            
            # Handle potential thinking output format
            if "</think>" in content:
                content = content.split("</think>\n\n")[-1]
                
            print("\nLLM Response:", content)
            return content
            
        except Exception as e:
            print(f"\nCritical LLM Error: {e}")
            raise RuntimeError(f"LLM failed to process request: {e}")

    def analyze_line_with_llm(self, line: str) -> Optional[Tuple[str, str, bool]]:
        """Ask LLM to analyze a log line and return regex, utility name, and error status"""
        prompt = f"""Analyze this log line and create a regex pattern for it:

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
   Regex: ^<\\d+>\\w{3}\\s+\\d{1,2}\\s+\\d{2}:\\d{2}:\\d{2}\\s+userdel\\[\\d+\\]:\\s+(.*)$
   Explanation: Only captures the message part, includes 'userdel' as identifier

2. For log: "Building target platforms: x86_64"
   Regex: ^Building target platforms: (\\w+)$
   Explanation: Captures platform name, uses exact phrase "Building target platforms" as identifier

Respond in JSON format with these fields:
{{
    "utility_name": "name of the program or unique identifier that generated this log",
    "regex": "regex pattern following the above rules",
}}"""
        print("\nAnalyzing log line with LLM:")
        print(prompt)
        
        try:
            response = self.ask_llm(prompt)
            
            # Remove markdown code block if present
            if response.startswith("```"):
                start = response.find("\n", response.find("```")) + 1
                end = response.rfind("```")
                response = response[start:end].strip()
            
            result = json.loads(response)
            
            # Validate the regex
            regex = result["regex"]
            re.compile(regex)  # Will raise re.error if invalid
            if not re.match(regex, line):
                print("Generated regex doesn't match the line")
                return None
                
            return regex, result["utility_name"], False
            
        except json.JSONDecodeError as e:
            print(f"\nFailed to parse LLM response as JSON: {e}")
            print(f"Raw response: {response}")
            raise RuntimeError(f"LLM provided invalid JSON response: {e}")
        except KeyError as e:
            print(f"\nLLM response missing required field: {e}")
            print(f"Raw response: {response}")
            raise RuntimeError(f"LLM response missing required field: {e}")
        except re.error as e:
            print(f"\nInvalid regex pattern: {e}")
            return None
        except Exception as e:
            print(f"\nError analyzing line: {e}")
            return None

    def process_unprocessed_log(self) -> bool:
        """Process a single unprocessed log file"""
        log = self.log_storage.get_random_unprocessed_log(limit=30)
        if not log:
            return False
            
        print(f"\nProcessing log: {log.packet_name} ({log.architecture})")
        print("=" * 80)
        
        # Track new patterns we create to avoid duplicates within same file
        new_patterns = set()
        llm_queries = 0
        
        for line_num, line in enumerate(log.log.splitlines(), 1):
            if not line.strip():
                continue
            
            print(f"\nLine {line_num}:")
            print(f"Content: {line}")
            print("-" * 40)
                
            # Try existing patterns first
            matched = False
            matching_pattern = None
            for pattern in self.patterns:  # Use cached patterns
                try:
                    if pattern.matches(line):
                        matched = True
                        matching_pattern = pattern
                        break
                except re.error:
                    continue
            
            if matched:
                print("Matched existing pattern:")
                print(f"  Utility: {matching_pattern.utility_name}")
                print(f"  Regex: {matching_pattern.regex}")
                print(f"  Is Error: {matching_pattern.is_error}")
                if matching_pattern.need_reviewing:
                    print("  ⚠️  This pattern needs review")
            else:
                print("Creating new pattern...")
                # Try to create a new pattern using LLM
                llm_queries += 1
                result = self.analyze_line_with_llm(line)
                if result:
                    regex, utility, is_error = result
                    # Check if we already created this pattern in this file
                    if regex not in new_patterns:
                        new_patterns.add(regex)
                        pattern_id = self._update_patterns(regex, utility, is_error)  # Update both DB and cache
                        print("Added new pattern:")
                        print(f"  Pattern ID: {pattern_id}")
                        print(f"  Utility: {utility}")
                        print(f"  Regex: {regex}")
                        print(f"  Is Error: {is_error}")
                    else:
                        print("Pattern already created in this file (skipping duplicate)")
                else:
                    print("Failed to create pattern for this line")
            
            print("-" * 80)
            
            # Allow user to pause after each line
            if line_num % 10 == 0:
                if input("\nPress Enter to continue, 'q' to quit processing this file: ").lower() == 'q':
                    break
        
        # Mark log as processed
        self.log_storage.mark_as_processed(log.id)
        print(f"\nFinished processing {log.packet_name}")
        
        # Print summary
        print("\nProcessing Summary:")
        print(f"Total new patterns created: {len(new_patterns)}")
        print("⚠️  All new patterns are marked for review")
        return True

    def run(self):
        """Process all unprocessed logs"""
        print("LLM Log Parser")
        print("=============")
        
        while self.process_unprocessed_log():
            pass
        
        print("\nAll logs processed!")

def main():
    parser = LLMParser()
    try:
        parser.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")

if __name__ == "__main__":
    main() 