# scrapers/socialinsider_scraper.py
from typing import Dict, Any
from scrapers.base_scraper import BaseScraper

class SocialInsiderScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "socialinsider"
        
    def scrape(self, username: str, headless: bool = False) -> Dict[str, Any]:
        # TODO: Implement SocialInsider specific scraping logic
        return {
            "source": self.source_name,
            "metrics": {}
        }
