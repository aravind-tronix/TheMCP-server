# csv_to_sqlite.py
import csv
import sqlite3
from pathlib import Path
import os

# Paths
CSV_PATH = Path(r"D:\Workbench\TheMCP\candidates.csv")
DB_PATH = Path(r"D:\Workbench\TheMCP\candidates.db")


def create_database():
    """Create SQLite database and candidates table from CSV."""
    # Ensure output directory exists
    os.makedirs(DB_PATH.parent, exist_ok=True)

    # Connect to SQLite database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create candidates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY,
                name TEXT,
                contact TEXT,
                cell TEXT,
                state TEXT,
                physical_assets TEXT,
                digital_assets TEXT,
                serving_notice TEXT,
                last_working_day TEXT,
                skills TEXT
            )
        """)

        # Read CSV and insert into table
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute("""
                    INSERT INTO candidates (id, name, contact, cell, state, physical_assets, digital_assets, serving_notice, last_working_day, skills)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(row["id"]),
                    row["name"],
                    row["contact"],
                    row["cell"],
                    row["state"],
                    row["physical_assets"],
                    row["digital_assets"],
                    row["serving_notice"],
                    row["last_working_day"],
                    row["skills"]
                ))

        # Commit and close
        conn.commit()
        print(
            f"Successfully created {DB_PATH} with {reader.line_num - 1} records.")
    except Exception as e:
        print(f"Error creating database: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    # Verify CSV exists
    if not CSV_PATH.exists():
        print(
            f"Error: {CSV_PATH} does not exist. Run create_candidates_csv.py first.")
    else:
        create_database()
