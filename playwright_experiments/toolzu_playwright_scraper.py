# playwright_experiments/toolzu_playwright_scraper.py
import sys
from playwright.sync_api import sync_playwright

def scrape_toolzu(username: str):
    """
    Experimental prototype using Playwright to scrape Toolzu.
    Demonstrates interception of requests and checking for Cloudflare blocking.
    """
    print(f"[playwright_experiment] Starting scrape for @{username} on Toolzu...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Run non-headless for testing
        page = browser.new_page()
        
        # Intercepting requests (e.g. to block images for faster loading, or capture API responses)
        def handle_route(route):
            if route.request.resource_type in ["image", "media"]:
                route.abort()
            else:
                route.continue_()
                
        page.route("**/*", handle_route)
        
        try:
            # Navigate to the target
            url = f"https://toolzu.com/profile-analyzer/instagram/?username={username}"
            print(f"[playwright_experiment] Navigating to {url}")
            page.goto(url, wait_until="networkidle")
            
            # Simple check to see if page loaded successfully or hit Cloudflare
            content = page.content()
            if "Just a moment" in content or "cf-browser-verification" in content:
                print("[playwright_experiment] WARNING: Cloudflare challenge detected!")
            else:
                print("[playwright_experiment] Page loaded successfully without immediate Cloudflare block.")
                
            # TODO: Add specific selectors for Toolzu data extraction here in the future
            
            # For now, just print the title
            print(f"[playwright_experiment] Page title: {page.title()}")
            
        except Exception as e:
            print(f"[playwright_experiment] Error during scraping: {e}")
        finally:
            browser.close()
            print("[playwright_experiment] Browser closed.")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "natgeo"
    scrape_toolzu(target)
