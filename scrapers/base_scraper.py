# scrapers/base_scraper.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseScraper(ABC):
    """
    Abstract base class for all influencer metric scrapers.
    Forces a consistent return structure.
    """
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the scraping source (e.g., 'nja', 'toolzu')."""
        pass
        
    @abstractmethod
    def scrape(self, username: str, headless: bool = False) -> Dict[str, Any]:
        """
        Scrape the profile data for the given username.
        
        Must return a dictionary in the format:
        {
            "source": self.source_name,
            "metrics": {
                # raw metrics extracted from the source
            }
        }
        """
        pass
