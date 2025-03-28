#!/usr/bin/env python3
import time
import json
import logging
from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

###############################################################################
#                               CONFIGURATION                                 #
###############################################################################

logging.basicConfig(level=logging.INFO)

# Define common scraping parameters
HEADLESS = True
SCROLL_DELAY = 3
MAX_SCROLLS = 3

# Filter parameters
LOCATION_KEYWORDS = ["houston", "htx"]
REQUIRED_ZIP = "77090"
REQUIRED_GENDER = "female"

OUTPUT_FILE = "filtered_social_profiles.json"

###############################################################################
#                            ABSTRACT BASE CLASSES                            #
###############################################################################

class BaseScraper(ABC):
    """
    Abstract base class enforcing a 'scrape_profiles' method signature.
    Each platform scraper will inherit and implement its own logic.
    """
    def __init__(self, driver):
        self.driver = driver

    @abstractmethod
    def scrape_profiles(self) -> list:
        """
        Perform platform-specific scraping and return a list of profile dictionaries.
        """
        pass

###############################################################################
#                              PLATFORM SCRAPERS                              #
###############################################################################

class TwitterScraper(BaseScraper):
    """
    Scrapes Twitter for user profiles based on a given search query.
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

        # Scroll to load more profiles
        for _ in range(self.max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_DELAY)

        # Extract data from search results
        try:
            user_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.css-1dbjc4n.r-1loqt21.r-18u37iz")
            logging.info(f"[TwitterScraper] Found {len(user_cards)} user cards in search.")
            for card in user_cards:
                username, bio = "unknown", ""
                try:
                    username_elem = card.find_element(By.CSS_SELECTOR, "div.css-901oao span")
                    username = username_elem.text.strip()
                except Exception:
                    pass
                try:
                    bio_elem = card.find_element(By.CSS_SELECTOR, "div.css-901oao+div")
                    bio = bio_elem.text.strip()
                except Exception:
                    pass

                profiles.append({
                    "platform": "Twitter",
                    "username": username,
                    "bio": bio,
                    "location": "unknown",  # Could be extracted by clicking profile
                    "gender": "",           # Placeholder
                    "url": ""               # Could parse from card attributes
                })
        except Exception as e:
            logging.error(f"[TwitterScraper] Error scraping profiles: {e}")

        return profiles


class InstagramScraper(BaseScraper):
    """
    Scrapes Instagram hashtag pages to find post links, from which we can
    theoretically derive user profiles. This is a simplified example.
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
        time.sleep(SCROLL_DELAY + 2)

        # Scroll to load more posts
        for _ in range(self.max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_DELAY)

        # Extract post links
        try:
            post_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/']")
            logging.info(f"[InstagramScraper] Found {len(post_links)} post links.")
            unique_links = {link.get_attribute("href") for link in post_links}

            for link_url in unique_links:
                profiles.append({
                    "platform": "Instagram",
                    "username": "unknown",
                    "bio": "unknown",
                    "location": "unknown",
                    "gender": "",  # Placeholder
                    "url": link_url
                })
        except Exception as e:
            logging.error(f"[InstagramScraper] Error scraping post links: {e}")

        return profiles


class FacebookScraper(BaseScraper):
    """
    Scrapes Facebook’s public search results for people. Note that Facebook often
    requires login or advanced dynamic handling, so real usage may need more steps.
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
                name = link.text.strip() if link.text else "unknown"
                profile_url = link.get_attribute("href")

                profiles.append({
                    "platform": "Facebook",
                    "username": name,
                    "bio": "",
                    "location": "unknown",
                    "gender": "",  # Placeholder
                    "url": profile_url
                })
        except Exception as e:
            logging.error(f"[FacebookScraper] Error scraping Facebook profiles: {e}")

        return profiles

###############################################################################
#                              SCRAPER MANAGER                                #
###############################################################################

class ScraperManager:
    """
    Orchestrates multiple platform scrapers, aggregates results, and
    can run filtering logic or pass data to external filters.
    """
    def __init__(self, headless=True):
        self.driver = self._init_driver(headless)
        self.scrapers = []

    def _init_driver(self, headless=True):
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        return webdriver.Chrome(options=options)

    def register_scraper(self, scraper: BaseScraper):
        self.scrapers.append(scraper)

    def run_all(self) -> list:
        """
        Runs scrape_profiles() on each registered scraper and
        aggregates the results into one list.
        """
        all_profiles = []
        for scraper in self.scrapers:
            try:
                platform_profiles = scraper.scrape_profiles()
                all_profiles.extend(platform_profiles)
            except Exception as e:
                logging.error(f"Error running scraper {scraper.__class__.__name__}: {e}")
        return all_profiles

    def close(self):
        self.driver.quit()

###############################################################################
#                               FILTERING LOGIC                               #
###############################################################################

class ProfileFilter:
    """
    A utility class for filtering profile data based on location, gender, or other criteria.
    """
    @staticmethod
    def filter_by_location(profiles: list, location_keywords: list, required_zip: str = None) -> list:
        filtered = []
        for profile in profiles:
            loc = profile.get("location", "").lower()
            if required_zip and required_zip in loc:
                filtered.append(profile)
            else:
                for keyword in location_keywords:
                    if keyword.lower() in loc:
                        filtered.append(profile)
                        break
        return filtered

    @staticmethod
    def filter_by_gender(profiles: list, gender: str = "female") -> list:
        # This example checks a 'gender' key, which might be empty if not scraped or inferred.
        return [p for p in profiles if p.get("gender", "").lower() == gender.lower()]

###############################################################################
#                                   MAIN                                      #
###############################################################################

def main():
    manager = ScraperManager(headless=HEADLESS)

    try:
        # Register scrapers for each platform
        tw_scraper = TwitterScraper(manager.driver, query="houston filter:users", max_scrolls=MAX_SCROLLS)
        ig_scraper = InstagramScraper(manager.driver, hashtag="houstonwomen", max_scrolls=MAX_SCROLLS)
        fb_scraper = FacebookScraper(manager.driver, query="Houston women", max_scrolls=MAX_SCROLLS)

        manager.register_scraper(tw_scraper)
        manager.register_scraper(ig_scraper)
        manager.register_scraper(fb_scraper)

        # Run scrapers
        all_profiles = manager.run_all()
        logging.info(f"Total scraped profiles: {len(all_profiles)}")

        # Filter by location
        local_profiles = ProfileFilter.filter_by_location(all_profiles, LOCATION_KEYWORDS, REQUIRED_ZIP)
        logging.info(f"Profiles after location filter: {len(local_profiles)}")

        # Filter by gender (placeholder, data likely missing in real usage)
        female_profiles = ProfileFilter.filter_by_gender(local_profiles, REQUIRED_GENDER)
        logging.info(f"Profiles after gender filter: {len(female_profiles)}")

        # Output to JSON
        with open(OUTPUT_FILE, "w") as f:
            json.dump(female_profiles, f, indent=4)
        logging.info(f"Filtered profiles saved to '{OUTPUT_FILE}'.")

    finally:
        # Always close the Selenium driver
        manager.close()

if __name__ == "__main__":
    main()