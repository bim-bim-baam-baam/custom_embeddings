import sqlite3
import sys
from pathlib import Path

MX_ROWS = 1000

def inspect_db(db_path):
    """Inspect a SQLite database file and print its structure and contents."""
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print(f"\nNo tables found in {db_path}")
            return
            
        print(f"\nDatabase: {db_path}")
        print("=" * 50)
        
        # For each table
        for (table_name,) in tables:
            print(f"\nTable: {table_name}")
            print("-" * 30)
            
            # Get column names
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            print("Columns:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"\nTotal rows: {count}")
            
            # Show sample data (first 5 rows)
            if count > 0:
                print("\nSample data (up to {MX_ROWS} rows):")
                cursor.execute(f"SELECT * FROM {table_name} LIMIT {MX_ROWS};")
                rows = cursor.fetchall()
                for row in rows:
                    print(f"  {row}")
            
            print("\n" + "=" * 50)
        
    except sqlite3.Error as e:
        print(f"Error accessing database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    # Default database paths
    db_paths = [
        "Data/db/patterns.db"
    ]
    
    # Allow specifying database path as argument
    if len(sys.argv) > 1:
        db_paths = [sys.argv[1]]
    
    for db_path in db_paths:
        if Path(db_path).exists():
            inspect_db(db_path)
        else:
            print(f"\nDatabase not found: {db_path}")

if __name__ == "__main__":
    main() 