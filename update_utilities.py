import sqlite3
from pathlib import Path

def load_whitelist(whitelist_path):
    """Load the whitelist of valid utility names"""
    with open(whitelist_path, 'r') as f:
        return {line.strip().lower() for line in f if line.strip()}

def update_utilities(db_path, whitelist_path):
    """Update utility names in the database based on whitelist"""
    # Load whitelist
    try:
        whitelist = load_whitelist(whitelist_path)
        print(f"Loaded {len(whitelist)} valid utility names from whitelist")
    except FileNotFoundError:
        print(f"Error: Whitelist file not found: {whitelist_path}")
        return
    
    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all columns from the patterns table
        cursor.execute("PRAGMA table_info(patterns)")
        columns = cursor.fetchall()
        text_columns = [col[1] for col in columns if col[2].upper() == 'TEXT']
        
        print("\nConverting text fields to lowercase:")
        total_updates = 0
        
        # Convert each text column to lowercase
        for column in text_columns:
            cursor.execute(f"UPDATE patterns SET {column} = LOWER({column})")
            rows_updated = cursor.rowcount
            total_updates += rows_updated
            print(f"- {column}: {rows_updated} values converted")
        
        # Get all unique utility names from database
        cursor.execute("SELECT DISTINCT utility_name FROM patterns")
        db_utilities = {row[0] for row in cursor.fetchall()}
        
        # Find utilities that need to be updated
        invalid_utilities = db_utilities - whitelist
        if not invalid_utilities:
            print("\nAll utility names in database are valid!")
            conn.commit()
            return
            
        print(f"\nFound {len(invalid_utilities)} invalid utility names:")
        for util in sorted(invalid_utilities):
            print(f"  - {util}")
            
        # Update invalid utilities to 'unknown'
        update_query = """
        UPDATE patterns 
        SET utility_name = 'unknown', need_reviewing = 1
        WHERE utility_name = ?
        """
        
        total_invalid = 0
        for util in invalid_utilities:
            cursor.execute(update_query, (util,))
            rows = cursor.rowcount
            total_invalid += rows
            print(f"Updated {rows} patterns for utility: {util}")
        
        conn.commit()
        print(f"\nSummary:")
        print(f"- Converted {total_updates} text values to lowercase")
        print(f"- Updated {total_invalid} patterns to 'unknown'")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    db_path = "Data/db/patterns.db"
    whitelist_path = "whitelist.txt"
    
    if not Path(db_path).exists():
        print(f"Error: Database file not found: {db_path}")
        return
        
    update_utilities(db_path, whitelist_path)

if __name__ == "__main__":
    main() 