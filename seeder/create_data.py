# create_candidates_csv.py
import requests
import csv
import os
from pathlib import Path
import random
import time
from datetime import datetime, timedelta

# Output CSV path
CSV_PATH = Path(r"D:\Workbench\TheMCP\candidates.csv")

# Possible assets and skills
PHYSICAL_ASSETS = ["mouse", "keyboard", "monitor", "desk", "chair", "printer",
                   "laptop", "desktop", "tablet", "smartphone", "headphones", "webcam", "external_hard_drive"]
DIGITAL_ASSETS = ["AWS", "Azure", "Google Cloud", "Office 365", "VPN", "antivirus",
                  "software_license", "CRM", "ERP", "project_management_tool", "communication_tool"]
SKILLS = ["Python", "Java", "JavaScript", "C++", "Ruby", "SQL", "Go", "TypeScript",
          "Docker", "Kubernetes", "Git", "Jenkins", "Terraform", "Ansible", "VS Code", "IntelliJ"]


def get_random_user(max_retries=3):
    """Fetch a random user from the API with retries."""
    for attempt in range(max_retries):
        try:
            response = requests.get("https://randomuser.me/api/", timeout=5)
            response.raise_for_status()
            data = response.json()
            if "results" in data and len(data["results"]) > 0:
                return data["results"][0]
            else:
                print(f"Empty results in attempt {attempt + 1}")
        except (requests.RequestException, ValueError) as e:
            print(f"Error fetching user in attempt {attempt + 1}: {e}")
        time.sleep(1)  # Wait before retrying
    return None


def generate_candidate(id):
    """Generate a candidate dictionary from API data."""
    user = get_random_user()
    if not user:
        return None

    # Randomly select 1-3 assets and 1-4 skills
    physical_assets = random.sample(PHYSICAL_ASSETS, random.randint(1, 3))
    digital_assets = random.sample(DIGITAL_ASSETS, random.randint(1, 3))
    skills = random.sample(SKILLS, random.randint(1, 4))

    # Determine serving notice (30% chance of True)
    serving_notice = random.random() < 0.3
    # Generate last working day (30-90 days from July 9, 2025) if serving notice
    last_working_day = ""
    if serving_notice:
        days_ahead = random.randint(30, 90)
        last_working_day = (datetime(2025, 7, 9) +
                            timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    return {
        "id": id,
        "name": f"{user['name']['first']} {user['name']['last']}",
        "contact": user["email"],
        "cell": user["cell"],
        "state": user["location"]["state"],
        "physical_assets": ",".join(physical_assets),
        "digital_assets": ",".join(digital_assets),
        # Store as 'true'/'false' for CSV compatibility
        "serving_notice": str(serving_notice).lower(),
        "last_working_day": last_working_day,
        "skills": ",".join(skills)
    }


def main():
    # Ensure output directory exists
    os.makedirs(CSV_PATH.parent, exist_ok=True)

    # Generate 100 candidates
    candidates = []
    i = 1
    while len(candidates) < 100 and i <= 150:  # Allow extra attempts to ensure 100 entries
        print(f"Generating candidate {i}")
        candidate = generate_candidate(i)
        if candidate:
            candidates.append(candidate)
        else:
            print(f"Failed to generate candidate {i}")
        i += 1

    # Write to CSV with UTF-8 encoding
    try:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["id", "name", "contact", "cell", "state", "physical_assets",
                               "digital_assets", "serving_notice", "last_working_day", "skills"])
            writer.writeheader()
            writer.writerows(candidates)
        print(
            f"Successfully created {CSV_PATH} with {len(candidates)} entries.")
    except Exception as e:
        print(f"Error writing CSV: {e}")


if __name__ == "__main__":
    main()
# This script generates a CSV file with 100 candidate entries, each containing random user data,
# physical and digital assets, skills, and serving notice information.
