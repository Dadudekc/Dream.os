#!/usr/bin/env python3
import time
import json
import logging
from abc import ABC, abstractmethod
from uuid import uuid4

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

###############################################################################
#                               CONFIGURATION                                 #
###############################################################################

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Common scraping parameters
HEADLESS = True
SCROLL_DELAY = 3
MAX_SCROLLS = 3

# Filter parameters
LOCATION_KEYWORDS = ["houston", "htx"]
REQUIRED_ZIP = "77090"
REQUIRED_GENDER = "female"

# Output file for the final results
OUTPUT_FILE = "filtered_social_profiles.json"

###############################################################################
#                               BASE SCRAPER                                  #
###############################################################################

class BaseScraper(ABC):
    """
    Abstract base class that enforces a 'scrape_profiles' method.
    Each platform-specific scraper will inherit and implement its own logic.
    """
    def __init__(self, driver: webdriver.Chrome):
        """
        :param driver: An initialized Selenium WebDriver instance.
        """
        self.driver = driver

    @abstractmethod
    def scrape_profiles(self) -> list:
        """
        Perform platform-specific scraping, returning a list of profile dictionaries.
        Each dictionary should at least have:
            {
              "platform": str,
              "username": str,
              "bio": str,
              "location": str,
              "gender": str,
              "url": str,
              "profile_id": str (unique ID)
            }
        """
        pass

###############################################################################
#                             PLATFORM SCRAPERS                               #
###############################################################################

class TwitterScraper(BaseScraper):
    """
    Scrapes Twitter user search results based on a text query.
    """
    SEARCH_URL_TEMPLATE = "https://twitter.com/search?q={query}&f=user"

    def __init__(self, driver, query="houston filter:users", max_scrolls=3):
        super().__init__(driver)
        self.query = query
        self.max_scrolls = max_scrolls

    def scrape_profiles(self) -> list:
        profiles = []
        search_url = self.SEARCH_URL_TEMPLATE.format(query=self.query.replace(" ", "%20"))
        logging.info(f"[TwitterScraper] Navigating to: {search_url}")

        self.driver.get(search_url)
        time.sleep(SCROLL_DELAY)

        # Scroll to load more user cards
        for _ in range(self.max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_DELAY)

        try:
            user_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.css-1dbjc4n.r-1loqt21.r-18u37iz")
            logging.info(f"[TwitterScraper] Found {len(user_cards)} user cards.")
            for card in user_cards:
                username = self._safe_get_text(card, "div.css-901oao span") or "unknown"
                bio = self._safe_get_text(card, "div.css-901oao+div") or ""
                profiles.append({
                    "platform": "Twitter",
                    "username": username,
                    "bio": bio,
                    "location": "unknown",  # Could parse by visiting each profile if needed
                    "gender": "",           # Placeholder for future inference
                    "url": "",              # Same note as above
                    "profile_id": str(uuid4())
                })
        except Exception as e:
            logging.error(f"[TwitterScraper] Error during scraping: {e}")

        return profiles

    def _safe_get_text(self, root, selector: str) -> str:
        """
        Safely extract text from a nested element in 'root' by CSS selector.
        """
        try:
            elem = root.find_element(By.CSS_SELECTOR, selector)
            return elem.text.strip()
        except:
            return ""

class InstagramScraper(BaseScraper):
    """
    Scrapes Instagram hashtag pages to find recent posts, used here as a proxy
    for user profiles. Real user data might require additional steps or logins.
    """
    HASHTAG_URL_TEMPLATE = "https://www.instagram.com/explore/tags/{hashtag}/"

    def __init__(self, driver, hashtag="houstonwomen", max_scrolls=3):
        super().__init__(driver)
        self.hashtag = hashtag
        self.max_scrolls = max_scrolls

    def scrape_profiles(self) -> list:
        profiles = []
        hashtag_url = self.HASHTAG_URL_TEMPLATE.format(hashtag=self.hashtag)
        logging.info(f"[InstagramScraper] Navigating to: {hashtag_url}")

        self.driver.get(hashtag_url)
        time.sleep(SCROLL_DELAY + 2)  # Extra delay for IG to load

        # Scroll to load more posts
        for _ in range(self.max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_DELAY)

        try:
            post_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/']")
            logging.info(f"[InstagramScraper] Found {len(post_links)} post links.")
            unique_links = {
                link.get_attribute("href") for link in post_links if link.get_attribute("href")
            }
            for link_url in unique_links:
                profiles.append({
                    "platform": "Instagram",
                    "username": "unknown",
                    "bio": "unknown",
                    "location": "unknown",
                    "gender": "",
                    "url": link_url,
                    "profile_id": str(uuid4())
                })
        except Exception as e:
            logging.error(f"[InstagramScraper] Error during scraping: {e}")

        return profiles

class FacebookScraper(BaseScraper):
    """
    Scrapes public Facebook "people" search results. Facebook often requires
    login or advanced dynamic handling, so YMMV with purely anonymous scraping.
    """
    SEARCH_URL_TEMPLATE = "https://www.facebook.com/search/people/?q={query}"

    def __init__(self, driver, query="Houston women", max_scrolls=3):
        super().__init__(driver)
        self.query = query
        self.max_scrolls = max_scrolls

    def scrape_profiles(self) -> list:
        profiles = []
        fb_search_url = self.SEARCH_URL_TEMPLATE.format(query=self.query.replace(" ", "%20"))
        logging.info(f"[FacebookScraper] Navigating to: {fb_search_url}")

        self.driver.get(fb_search_url)
        time.sleep(SCROLL_DELAY + 2)

        # Scroll to load more results
        for _ in range(self.max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_DELAY)

        try:
            result_links = self.driver.find_elements(By.CSS_SELECTOR, "div[data-pagelet='MainFeed'] a")
            logging.info(f"[FacebookScraper] Found {len(result_links)} result links.")
            for link in result_links:
                name = link.text.strip() or "unknown"
                profile_url = link.get_attribute("href") or ""
                profiles.append({
                    "platform": "Facebook",
                    "username": name,
                    "bio": "",
                    "location": "unknown",
                    "gender": "",
                    "url": profile_url,
                    "profile_id": str(uuid4())
                })
        except Exception as e:
            logging.error(f"[FacebookScraper] Error during scraping: {e}")

        return profiles

###############################################################################
#                              SCRAPER MANAGER                                #
###############################################################################

class ScraperManager:
    """
    Orchestrates multiple platform scrapers, aggregates their results,
    and manages the Selenium WebDriver lifecycle.
    """
    def __init__(self, headless=True):
        self.driver = self._init_driver(headless)
        self.scrapers = []

    def _init_driver(self, headless: bool) -> webdriver.Chrome:
        """
        Initialize a Chrome WebDriver with the specified options.
        """
        options = Options()
        if headless:
            options.add_argument("--headless")
        # Helps avoid detection by some sites
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        return webdriver.Chrome(options=options)

    def register_scraper(self, scraper: BaseScraper):
        """
        Manually register a new scraper instance.
        """
        self.scrapers.append(scraper)

    def register_default_scrapers(self):
        """
        Register Twitter, Instagram, and Facebook scrapers
        with default queries and scroll settings.
        """
        self.register_scraper(
            TwitterScraper(self.driver, query="houston filter:users", max_scrolls=MAX_SCROLLS)
        )
        self.register_scraper(
            InstagramScraper(self.driver, hashtag="houstonwomen", max_scrolls=MAX_SCROLLS)
        )
        self.register_scraper(
            FacebookScraper(self.driver, query="Houston women", max_scrolls=MAX_SCROLLS)
        )

    def run_all(self) -> list:
        """
        Runs scrape_profiles() on each registered scraper, returning a combined list.
        """
        all_results = []
        for scraper in self.scrapers:
            try:
                scraped = scraper.scrape_profiles()
                all_results.extend(scraped)
            except Exception as e:
                logging.error(f"[ScraperManager] Failed running {scraper.__class__.__name__}: {e}")
        return all_results

    def close(self):
        """
        Closes the WebDriver instance to free up resources.
        """
        self.driver.quit()

###############################################################################
#                             FILTERING LOGIC                                 #
###############################################################################

class ProfileFilter:
    """
    A utility class to filter scraped profiles by location, gender, or any custom rules.
    """

    @staticmethod
    def filter_by_location(profiles: list, location_keywords: list, required_zip: str = None) -> list:
        """
        Keeps profiles if their location contains the required zip or any of the keywords.
        """
        filtered = []
        for p in profiles:
            loc = p.get("location", "").lower()
            if required_zip and required_zip in loc:
                filtered.append(p)
            elif any(k in loc for k in location_keywords):
                filtered.append(p)
        return filtered

    @staticmethod
    def filter_by_gender(profiles: list, gender="female") -> list:
        """
        Keeps profiles where p['gender'].lower() == gender.lower().
        """
        return [p for p in profiles if p.get("gender", "").lower() == gender.lower()]

###############################################################################
#                                   MAIN                                      #
###############################################################################

def main():
    """
    Main entry point that:
      1. Initializes the ScraperManager in headless mode.
      2. Registers default scrapers (Twitter, Instagram, Facebook).
      3. Collects and logs all scraped profiles.
      4. Applies location and gender filters.
      5. Saves final results to OUTPUT_FILE in JSON format.
    """
    manager = ScraperManager(headless=HEADLESS)
    try:
        logging.info("[Main] Registering default scrapers...")
        manager.register_default_scrapers()

        logging.info("[Main] Running all scrapers...")
        all_profiles = manager.run_all()
        logging.info(f"[Main] Total scraped: {len(all_profiles)} profiles")

        # Filter by location
        loc_filtered = ProfileFilter.filter_by_location(all_profiles, LOCATION_KEYWORDS, REQUIRED_ZIP)
        logging.info(f"[Main] Profiles after location filter: {len(loc_filtered)}")

        # Filter by gender
        gender_filtered = ProfileFilter.filter_by_gender(loc_filtered, REQUIRED_GENDER)
        logging.info(f"[Main] Profiles after gender filter: {len(gender_filtered)}")

        # Save results
        with open(OUTPUT_FILE, "w") as f:
            json.dump(gender_filtered, f, indent=4)
        logging.info(f"[Main] Final results saved to '{OUTPUT_FILE}'.")

    finally:
        manager.close()

if __name__ == "__main__":
    main()
