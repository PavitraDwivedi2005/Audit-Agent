# playwright_experiments/nja_api_investigator.py
import sys
import time
from playwright.sync_api import sync_playwright

def investigate_nja(username: str):
    """
    Experimental prototype using Playwright to inspect NotJustAnalytics 
    API endpoints and XHR requests for potential interception.
    """
    print(f"[playwright_experiment] Starting XHR investigation for @{username} on NJA...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # We will track all XHR/Fetch requests
        intercepted_apis = []

        def handle_response(response):
            if response.request.resource_type in ["xhr", "fetch"]:
                url = response.url
                # Filter out obvious tracking/analytics
                if "google-analytics" not in url and "clarity.ms" not in url:
                    status = response.status
                    print(f"[XHR DETECTED] [{status}] {url}")
                    # Try to parse JSON to see what data they return
                    if "application/json" in response.headers.get("content-type", ""):
                        try:
                            data = response.json()
                            print(f"   -> JSON Response keys: {list(data.keys()) if isinstance(data, dict) else 'List/Other'}")
                        except Exception:
                            pass
        
        page.on("response", handle_response)
        
        try:
            url = f"https://app.notjustanalytics.com/analysis/{username}"
            print(f"[playwright_experiment] Navigating to {url}")
            page.goto(url, wait_until="networkidle")
            
            # Scroll to trigger lazy loading
            for i in range(5):
                page.mouse.wheel(0, 1000)
                time.sleep(1)
            
            # Simple check to see if page loaded successfully or hit Cloudflare
            content = page.content()
            if "Just a moment" in content or "cf-browser-verification" in content:
                print("[playwright_experiment] WARNING: Cloudflare challenge detected!")
            else:
                print("[playwright_experiment] Page loaded successfully.")
                
            print(f"[playwright_experiment] Page title: {page.title()}")
            
        except Exception as e:
            print(f"[playwright_experiment] Error during scraping: {e}")
        finally:
            browser.close()
            print("[playwright_experiment] Browser closed.")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "natgeo"
    investigate_nja(target)
