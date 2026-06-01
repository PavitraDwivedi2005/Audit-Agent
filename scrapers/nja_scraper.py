# scrapers/nja_scraper.py
import os
import time
import platform
from typing import Dict, Any

import undetected_chromedriver as uc
from scrapers.base_scraper import BaseScraper
from extractor import EXTRACT_JS, validate_result, clean_result

class NJAScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "nja"

    def _detect_chrome_version(self) -> int | None:
        if platform.system() == "Windows":
            import winreg
            for hive, subkey in [
                (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Google\Chrome\BLBeacon"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Google\Chrome\BLBeacon"),
            ]:
                try:
                    key = winreg.OpenKey(hive, subkey)
                    version, _ = winreg.QueryValueEx(key, "version")
                    winreg.CloseKey(key)
                    major = int(version.split(".")[0])
                    print(f"[{self.source_name}] Detected Chrome version: {version} (major={major})")
                    return major
                except (FileNotFoundError, OSError, ValueError):
                    continue
        else:
            import subprocess
            for cmd in ["google-chrome --version", "chromium --version"]:
                try:
                    out = subprocess.check_output(cmd, shell=True, text=True).strip()
                    major = int(out.split()[-1].split(".")[0])
                    print(f"[{self.source_name}] Detected Chrome version: {out} (major={major})")
                    return major
                except Exception:
                    continue
        
        print(f"[{self.source_name}] Could not auto-detect Chrome version, letting UC decide.")
        return None

    def _wait_for_data(self, driver, timeout: int = 45) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                body_text = driver.execute_script("return document.body.innerText || '';")
                if isinstance(body_text, str):
                    if "Followers" in body_text and "Avg" in body_text:
                        time.sleep(1.5)
                        return True
                    if "Checking" in body_text or "Just a moment" in body_text:
                        print(f"[{self.source_name}] Cloudflare challenge page detected, waiting...")
                    elif "Page not found" in body_text or "404" in body_text:
                        raise RuntimeError(
                            "Profile not found on NotJustAnalytics. "
                            "Make sure the username is correct."
                        )
            except RuntimeError:
                raise
            except Exception:
                pass
            time.sleep(1.5)
        return False

    def scrape(self, username: str, headless: bool = False) -> Dict[str, Any]:
        print(f"[{self.source_name}] Launching Chrome for @{username}...")
        
        chrome_ver = self._detect_chrome_version()
        
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        
        if headless:
            options.add_argument("--headless=new")
            
        driver = uc.Chrome(options=options, version_main=chrome_ver)
        
        try:
            url = f"https://app.notjustanalytics.com/analysis/{username}"
            print(f"[{self.source_name}] Navigating to {url}")
            driver.get(url)
            
            print(f"[{self.source_name}] Waiting for analytics data to load...")
            loaded = self._wait_for_data(driver, timeout=45)
            
            if not loaded:
                raise RuntimeError(
                    "Timed out waiting for analytics data. "
                    "The page may still be behind a Cloudflare challenge, "
                    "or the username doesn't exist on NotJustAnalytics."
                )
                
            # --- Progressive Scrolling ---
            print(f"[{self.source_name}] Beginning progressive scroll for deep analytics...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            while scroll_attempts < 8:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2.5)  # wait for lazy-loading sections (charts, hashtags)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    print(f"[{self.source_name}] Reached bottom of page.")
                    break
                print(f"[{self.source_name}] Scrolled to new height: {new_height}")
                last_height = new_height
                scroll_attempts += 1
                
            print(f"[{self.source_name}] Extracting metrics via JavaScript...")
            result = driver.execute_script(EXTRACT_JS)
            
            if not isinstance(result, dict):
                raise RuntimeError(f"JS extractor returned unexpected type: {type(result).__name__}")
                
            if not validate_result(result):
                print(f"[{self.source_name}] Metrics look empty — waiting 6s and retrying...")
                time.sleep(6)
                result = driver.execute_script(EXTRACT_JS)
                
                if not isinstance(result, dict) or not validate_result(result):
                    raise RuntimeError("Extracted data has zero followers after retry.")
                    
            result = clean_result(result, username)
            print(f"[{self.source_name}] Done! Extracted data for @{username}")
            
            return {
                "source": self.source_name,
                "metrics": result
            }
            
        finally:
            driver.quit()
            print(f"[{self.source_name}] Browser closed.")
