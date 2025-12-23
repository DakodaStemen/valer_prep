"""Selenium-based web scraper for healthcare portal automation."""

import os
import logging
from typing import List, Dict, Optional, Generator
from contextlib import contextmanager

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    NoSuchElementException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

logger = logging.getLogger(__name__)


class PortalScraper:
    """Scraper for healthcare portal automation."""

    def __init__(self, headless: bool = True, timeout: int = 30) -> None:
        """Initialize PortalScraper.

        Args:
            headless: Run browser in headless mode
            timeout: Default timeout for WebDriverWait in seconds
        """
        self.headless = headless
        self.timeout = timeout
        self.driver: Optional[webdriver.Chrome] = None

    def _create_driver(self) -> webdriver.Chrome:
        """Create and configure Chrome WebDriver instance.

        Returns:
            Configured Chrome WebDriver instance

        Raises:
            WebDriverException: If driver creation fails
        """
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.implicitly_wait(5)
            return driver
        except WebDriverException as e:
            logger.error(f"Failed to create WebDriver: {e}")
            raise

    @contextmanager
    def _driver_context(self) -> Generator[webdriver.Chrome, None, None]:
        """Context manager for WebDriver lifecycle.

        Ensures driver.quit() is always called, even on exceptions.
        """
        driver = None
        try:
            driver = self._create_driver()
            self.driver = driver
            yield driver
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    logger.warning(f"Error closing driver: {e}")
                finally:
                    self.driver = None

    def login(self, username: str, password: str) -> bool:
        """Simulate login to healthcare portal.

        Args:
            username: Portal username
            password: Portal password

        Returns:
            True if login successful, False otherwise
        """
        if not self.driver:
            raise RuntimeError("Driver not initialized. Use context manager or call _create_driver() first.")

        login_url = "https://the-internet.herokuapp.com/login"
        logger.info(f"Navigating to login page: {login_url}")

        try:
            self.driver.get(login_url)

            wait = WebDriverWait(self.driver, self.timeout)

            username_field = wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            password_field = wait.until(
                EC.presence_of_element_located((By.ID, "password"))
            )
            login_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )

            username_field.clear()
            username_field.send_keys(username)

            password_field.clear()
            password_field.send_keys(password)

            login_button.click()

            wait.until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".flash.success")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".flash.error")),
                )
            )

            success_indicator = self.driver.find_elements(By.CSS_SELECTOR, ".flash.success")
            if success_indicator:
                logger.info("Login successful")
                return True
            else:
                logger.warning("Login may have failed - no success indicator found")
                return False

        except TimeoutException as e:
            logger.error(f"Timeout during login: {e}")
            return False
        except (StaleElementReferenceException, NoSuchElementException) as e:
            logger.error(f"Element not found or stale during login: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            return False

    def get_authorizations(self) -> List[Dict[str, str]]:
        """Extract patient authorization data from portal table.

        Returns:
            List of dictionaries containing patient authorization data

        Raises:
            RuntimeError: If driver not initialized
            TimeoutException: If table elements not found within timeout
        """
        if not self.driver:
            raise RuntimeError("Driver not initialized. Use context manager or call _create_driver() first.")

        tables_url = "https://the-internet.herokuapp.com/tables"
        logger.info(f"Navigating to tables page: {tables_url}")

        try:
            self.driver.get(tables_url)

            wait = WebDriverWait(self.driver, self.timeout)

            table = wait.until(
                EC.presence_of_element_located((By.ID, "table1"))
            )

            rows = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#table1 tbody tr"))
            )

            authorizations: List[Dict[str, str]] = []

            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 4:
                        continue

                    last_name = cells[0].text.strip()
                    first_name = cells[1].text.strip()
                    due_amount = cells[3].text.strip()

                    patient_name = f"{first_name} {last_name}".strip()
                    auth_number = due_amount.replace("$", "").replace(",", "").strip()

                    if patient_name and auth_number:
                        authorizations.append({
                            "patient_name": patient_name,
                            "auth_number": auth_number,
                            "status": "Pending",
                        })
                except StaleElementReferenceException:
                    logger.warning("Stale element reference encountered, skipping row")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing row: {e}")
                    continue

            logger.info(f"Extracted {len(authorizations)} authorization records")
            return authorizations

        except TimeoutException as e:
            logger.error(f"Timeout while extracting authorizations: {e}")
            raise
        except StaleElementReferenceException as e:
            logger.error(f"Stale element reference: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error extracting authorizations: {e}")
            raise

    def run_full_extraction(self, username: str, password: str) -> List[Dict[str, str]]:
        """Execute full workflow: login and extract authorizations.

        Args:
            username: Portal username
            password: Portal password

        Returns:
            List of authorization records

        Raises:
            RuntimeError: If login fails or extraction fails
        """
        with self._driver_context():
            if not self.login(username, password):
                raise RuntimeError("Login failed, cannot proceed with extraction")

            return self.get_authorizations()

