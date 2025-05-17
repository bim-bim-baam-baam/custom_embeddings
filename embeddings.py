from log_patterns import LogPatternStore
from log_storage import LogStorage
import numpy as np
from typing import Dict, List, Tuple
import re

class EmbeddingGenerator:
    def __init__(self, pattern_db_path: str = "Data/db/patterns.db"):
        self.pattern_store = LogPatternStore(pattern_db_path)
        self._utility_mapping: Dict[str, int] = {}
        self._patterns_by_utility: Dict[str, List[Tuple[str, bool]]] = {}
        self._initialize_mappings()

    def _initialize_mappings(self):
        """Initialize utility name to index mapping and patterns grouping"""
        # Get all patterns and group them by utility
        patterns = self.pattern_store.get_all_patterns()
        
        # Group patterns by utility name
        utility_patterns: Dict[str, List[Tuple[str, bool]]] = {}
        for pattern in patterns:
            if pattern.utility_name not in utility_patterns:
                utility_patterns[pattern.utility_name] = []
            utility_patterns[pattern.utility_name].append((pattern.regex, pattern.is_error))
        
        # Create mapping of utility names to indices
        self._utility_mapping = {name: idx for idx, name in enumerate(sorted(utility_patterns.keys()))}
        self._patterns_by_utility = utility_patterns
        
    @property
    def dimension(self) -> int:
        """Get the dimension of the embedding vector (number of unique utilities)"""
        return len(self._utility_mapping)
    
    @property
    def utility_names(self) -> List[str]:
        """Get list of utility names in order of their indices"""
        return [name for name, _ in sorted(self._utility_mapping.items(), key=lambda x: x[1])]

    def generate_embedding(self, log_content: str) -> np.ndarray:
        """Generate embedding vector for a log file.
        
        The vector will have dimension equal to number of unique utilities.
        Each element represents the count of error lines from that utility.
        
        Args:
            log_content: Content of the log file as string
            
        Returns:
            numpy array of shape (n_utilities,) containing error counts
        """
        # Initialize zero vector
        embedding = np.zeros(self.dimension)
        
        # Process each line
        for line in log_content.splitlines():
            if not line.strip():
                continue
                
            # Try each utility's patterns
            for utility_name, patterns in self._patterns_by_utility.items():
                utility_idx = self._utility_mapping[utility_name]
                
                # Try each pattern for this utility
                for regex, is_error in patterns:
                    try:
                        if re.match(regex, line):
                            # If pattern matches and is error pattern, increment count
                            if is_error:
                                embedding[utility_idx] += 1
                            # Break inner loop - we found a matching pattern
                            break
                    except re.error:
                        continue
        
        return embedding

def main():
    # Example usage
    generator = EmbeddingGenerator()
    
    print("Utility name mappings:")
    for name, idx in sorted(generator._utility_mapping.items(), key=lambda x: x[1]):
        print(f"{name}")
    
    print(f"\nEmbedding dimension: {generator.dimension}")
    
    # Example with a sample log
    sample_log = """<86>May 16 05:13:18 userdel[616177]: delete user 'rooter'
<86>May 16 05:13:19 useradd[616178]: new user added 'admin'
Building target platforms: x86_64"""
    
    embedding = generator.generate_embedding(sample_log)
    print("\nSample log embedding:")
    for idx, count in enumerate(embedding):
        print(f"{generator.utility_names[idx]}: {count} errors")

if __name__ == "__main__":
    main() 