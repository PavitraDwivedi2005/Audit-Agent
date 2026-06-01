# scraper.py
# Adapter to maintain compatibility with existing Streamlit app
import json
import sys
import os

from scrapers.nja_scraper import NJAScraper

def get_profile_data(username: str, headless: bool = False) -> dict:
    """
    Adapter function to maintain compatibility with existing Streamlit app.
    Uses the new NJAScraper architecture.
    """
    scraper = NJAScraper()
    result = scraper.scrape(username, headless=headless)
    # The new scraper returns {"source": "nja", "metrics": {...}}
    # The old app expects just the metrics dict with username included
    return result["metrics"]

def save_to_json(data: dict, filepath: str = "info.JSON"):
    """Save scraped data to a JSON file next to this script. Maintained for compatibility."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(script_dir, filepath)
    with open(full_path, "w") as f:
        json.dump(data, f, indent=4)
    print(f"[scraper] Saved to {full_path}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "raahavy_"
    data = get_profile_data(target)
    save_to_json(data)
    print("\n--- Result ---")
    print(json.dumps(data, indent=4))
