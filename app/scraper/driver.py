from typing import Tuple

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait

from app.config.constants import WEBDRIVER_WAIT_TIMEOUT, DATA_DIR
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class Driver:
    """Context manager for managing the Chrome WebDriver."""

    def __init__(self, wait=WEBDRIVER_WAIT_TIMEOUT['short'], download_dir=DATA_DIR) -> None:
        self.wait_timeout = wait
        self.download_dir = download_dir

    def __enter__(self) -> Tuple[Chrome, WebDriverWait]:
        # Setup the Chrome options.
        options = ChromeOptions()

        # Add headless mode option for background operations.
        # options.add_argument("--headless") # Uncomment for headless mode

        options.add_argument('--enable-chrome-browser-cloud-management')
        options.add_argument('--disable-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.page_load_strategy = 'normal'
        options.add_experimental_option('prefs', {
            'download.default_directory': self.download_dir,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'plugin.always_open_pdf_externally': True
        })

        # Initialize the Chrome driver with the options.
        driver = Chrome(options=options)
        wait = WebDriverWait(driver, self.wait_timeout)

        return driver, wait

    def __exit__(self, exc_type, exc_val, traceback) -> None:
        if hasattr(self, 'driver'):
            self.driver.quit()

        if exc_type is not None:
            logger.error(f"An error occurred: {exc_val}")
