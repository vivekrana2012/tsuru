#!/usr/bin/env python3
"""Simple SQLite database query tool for Tsuru RSS Feed Manager"""
import sqlite3
import os
import sys
from datetime import datetime

# Database path
DATA_DIR = os.getenv('DATA_DIR', '.')
DB_PATH = os.path.join(DATA_DIR, 'rss_feed.db')


def print_table(cursor, headers):
    """Print query results in a formatted table"""
    rows = cursor.fetchall()
    
    if not rows:
        print("No results found.\n")
        return
    
    # Calculate column widths
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val) if val else "NULL"))
    
    # Print header
    header_line = " | ".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
    print("\n" + header_line)
    print("-" * len(header_line))
    
    # Print rows
    for row in rows:
        row_line = " | ".join(str(val if val is not None else "NULL").ljust(w) 
                              for val, w in zip(row, col_widths))
        print(row_line)
    
    print(f"\nTotal rows: {len(rows)}\n")


def show_users():
    """Show all users"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, created_at, CASE WHEN password IS NULL THEN 'NOT SET' ELSE 'SET' END as password_status FROM users")
        print_table(cursor, ["ID", "Username", "Created At", "Password"])


def show_feed(limit=20):
    """Show feed entries"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT id, title, url, added_by, tts_enabled, 
                   CASE WHEN audio_path IS NULL THEN 'No' ELSE 'Yes' END as has_audio,
                   created_at 
            FROM feed 
            ORDER BY created_at DESC 
            LIMIT {limit}
        """)
        print_table(cursor, ["ID", "Title", "URL", "Added By", "TTS", "Audio", "Created At"])


def show_tts_queue():
    """Show TTS queue entries"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, status, added_by, created_at, 
                   CASE WHEN error_message IS NULL THEN '' ELSE error_message END as error
            FROM tts_queue 
            ORDER BY created_at DESC
        """)
        print_table(cursor, ["ID", "Title", "Status", "Added By", "Created At", "Error"])


def custom_query(query):
    """Execute a custom SQL query"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            if cursor.description:
                headers = [desc[0] for desc in cursor.description]
                print_table(cursor, headers)
            else:
                print("Query executed successfully.\n")
        except sqlite3.Error as e:
            print(f"Error: {e}\n")


def show_menu():
    """Display interactive menu"""
    while True:
        print("=" * 50)
        print("Tsuru Database Query Tool")
        print("=" * 50)
        print("1. Show all users")
        print("2. Show feed entries (last 20)")
        print("3. Show TTS queue")
        print("4. Custom SQL query")
        print("5. Show feed entries (all)")
        print("6. Exit")
        print("=" * 50)
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            print("\n### USERS TABLE ###")
            show_users()
        elif choice == "2":
            print("\n### FEED ENTRIES (Last 20) ###")
            show_feed(20)
        elif choice == "3":
            print("\n### TTS QUEUE ###")
            show_tts_queue()
        elif choice == "4":
            query = input("\nEnter SQL query: ").strip()
            if query:
                print(f"\n### CUSTOM QUERY RESULTS ###")
                custom_query(query)
        elif choice == "5":
            print("\n### ALL FEED ENTRIES ###")
            show_feed(1000)
        elif choice == "6":
            print("Goodbye!\n")
            break
        else:
            print("Invalid choice. Please try again.\n")
        
        input("Press Enter to continue...")
        print("\n")


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)
    
    # Check for command-line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "users":
            show_users()
        elif sys.argv[1] == "feed":
            show_feed(1000)
        elif sys.argv[1] == "queue":
            show_tts_queue()
        elif sys.argv[1] == "query":
            if len(sys.argv) > 2:
                custom_query(" ".join(sys.argv[2:]))
            else:
                print("Usage: python query_db.py query 'SELECT * FROM feed'")
        else:
            print("Usage:")
            print("  python query_db.py              # Interactive mode")
            print("  python query_db.py users        # Show users")
            print("  python query_db.py feed         # Show feed entries")
            print("  python query_db.py queue        # Show TTS queue")
            print("  python query_db.py query 'SQL'  # Custom query")
    else:
        # Interactive mode
        show_menu()
