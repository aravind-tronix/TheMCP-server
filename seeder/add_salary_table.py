# add_salary_table.py
import sqlite3
from contextlib import closing
from pathlib import Path
import os
import random

# Database path
DB_PATH = Path(r"D:\Workbench\TheMCP\candidates.db")

# Sample salary structures
SALARY_STRUCTURES = [
    "$50,000/year, 10% bonus",
    "$60,000/year, stock options",
    "$45,000/year, 5% bonus",
    "₹40,00,000/year, health insurance",
    "₹50,00,000/year, 15% bonus",
    "$70,000/year, remote allowance",
    "₹35,00,000/year, stock options",
    "$55,000/year, 401k match"
]


def create_salary_table():
    """Create salary_structure table, populate it, and create a view."""
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            cursor = conn.cursor()

            # Create salary_structure table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS salary_structure (
                    id INTEGER PRIMARY KEY,
                    salary_structure TEXT,
                    FOREIGN KEY (id) REFERENCES candidates(id)
                )
            """)

            # Populate salary_structure for ids 1 to 100
            cursor.executemany("""
                INSERT OR REPLACE INTO salary_structure (id, salary_structure)
                VALUES (?, ?)
            """, [(i, random.choice(SALARY_STRUCTURES)) for i in range(1, 101)])

            # Create view joining candidates and salary_structure
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS candidate_salary_view AS
                SELECT 
                    c.id,
                    c.name,
                    c.contact,
                    c.cell,
                    c.state,
                    c.physical_assets,
                    c.digital_assets,
                    c.serving_notice,
                    c.last_working_day,
                    c.skills,
                    s.salary_structure
                FROM candidates c
                LEFT JOIN salary_structure s ON c.id = s.id
            """)

            conn.commit()
            print(
                f"Successfully created salary_structure table and candidate_salary_view in {DB_PATH}.")
    except Exception as e:
        print(f"Error updating database: {e}")


if __name__ == "__main__":
    # Verify database exists
    if not DB_PATH.exists():
        print(f"Error: {DB_PATH} does not exist. Run csv_to_sqlite.py first.")
    else:
        create_salary_table()
