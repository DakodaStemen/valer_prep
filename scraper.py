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

        Uses explicit waits at each step to handle slow-loading portals.
        Demonstrates proper wait strategies for form interactions.

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

            # Wait for page to be fully loaded before interacting
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")

            # Wait for form to be present and visible (not just in DOM)
            wait.until(
                EC.presence_of_element_located((By.ID, "login"))
            )

            # Wait for username field to be visible and interactable
            username_field = wait.until(
                EC.visibility_of_element_located((By.ID, "username"))
            )
            wait.until(EC.element_to_be_clickable((By.ID, "username")))

            # Wait for password field to be visible and interactable
            password_field = wait.until(
                EC.visibility_of_element_located((By.ID, "password"))
            )
            wait.until(EC.element_to_be_clickable((By.ID, "password")))

            # Wait for login button to be clickable (ensures form is ready)
            login_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )

            # Clear and fill fields with explicit waits between actions
            username_field.clear()
            wait.until(lambda _: username_field.get_attribute("value") == "" or username_field.get_attribute("value") is None)
            username_field.send_keys(username)
            wait.until(lambda _: username_field.get_attribute("value") == username)

            password_field.clear()
            wait.until(lambda _: password_field.get_attribute("value") == "" or password_field.get_attribute("value") is None)
            password_field.send_keys(password)
            wait.until(lambda _: password_field.get_attribute("value") == password)

            # Click login button and wait for navigation/response
            login_button.click()

            # Wait for either success or error message to appear (handles slow responses)
            wait.until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".flash.success")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".flash.error")),
                )
            )

            # Additional wait to ensure flash message is visible
            wait.until(
                EC.any_of(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, ".flash.success")),
                    EC.visibility_of_element_located((By.CSS_SELECTOR, ".flash.error")),
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

        Uses explicit waits throughout to handle slow-loading portals gracefully.
        Implements retry logic for stale elements to demonstrate robust error handling.

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

            # Wait for page to be fully loaded (explicit wait for document ready)
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")

            # Wait for table to be present and visible (not just in DOM)
            wait.until(
                EC.visibility_of_element_located((By.ID, "table1"))
            )

            # Wait for table body to be present before looking for rows
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#table1 tbody"))
            )

            # Wait for at least one row to be present (handles slow-loading tables)
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#table1 tbody tr"))
            )

            # Additional wait to ensure all rows are loaded (explicit wait for multiple elements)
            rows = wait.until(
                lambda driver: driver.find_elements(By.CSS_SELECTOR, "#table1 tbody tr")
            )

            if not rows:
                logger.warning("No rows found in table")
                return []

            logger.info(f"Found {len(rows)} rows to process")

            authorizations: List[Dict[str, str]] = []
            max_retries = 3

            for idx, row in enumerate(rows):
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        # Re-find row on each retry to avoid stale element
                        if retry_count > 0:
                            rows = self.driver.find_elements(By.CSS_SELECTOR, "#table1 tbody tr")
                            if idx >= len(rows):
                                break
                            row = rows[idx]

                        # Wait for cells to be present within the row
                        cells = WebDriverWait(row, 10).until(
                            lambda r: r.find_elements(By.TAG_NAME, "td")
                        )

                        if len(cells) < 4:
                            logger.warning(f"Row {idx + 1} has insufficient cells, skipping")
                            break

                        # Bind cell to local variable to avoid closure bug
                        cell_0 = cells[0]
                        cell_1 = cells[1]
                        cell_3 = cells[3]

                        # Wait for cell text to be non-empty (handles slow-rendering content)
                        # We use lambda d: ... to accept the driver argument from wait.until but ignore it,
                        # accessing cell_0 directly from the closure.
                        last_name_cell = wait.until(
                            lambda d: cell_0.text.strip() if cell_0.text.strip() else None
                        )
                        first_name_cell = cell_1.text.strip()
                        due_amount_cell = cell_3.text.strip()

                        if not last_name_cell or not due_amount_cell:
                            logger.warning(f"Row {idx + 1} has empty required fields, skipping")
                            break

                        patient_name = f"{first_name_cell} {last_name_cell}".strip()
                        auth_number = due_amount_cell.replace("$", "").replace(",", "").strip()

                        if patient_name and auth_number:
                            authorizations.append({
                                "patient_name": patient_name,
                                "auth_number": auth_number,
                                "status": "Pending",
                            })
                            break
                        else:
                            # If patient_name or auth_number is empty after processing, skip this row
                            logger.warning(f"Row {idx + 1} has invalid data after processing (empty name or auth_number), skipping")
                            break

                    except StaleElementReferenceException:
                        retry_count += 1
                        if retry_count < max_retries:
                            logger.debug(f"Stale element on row {idx + 1}, retrying ({retry_count}/{max_retries})")
                            continue
                        else:
                            logger.warning(f"Stale element on row {idx + 1} after {max_retries} retries, skipping")
                            break
                    except TimeoutException:
                        logger.warning(f"Timeout waiting for row {idx + 1} content, skipping")
                        break
                    except Exception as e:
                        logger.warning(f"Error processing row {idx + 1}: {e}")
                        break

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

