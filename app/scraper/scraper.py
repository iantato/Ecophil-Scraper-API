from typing import Tuple

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from app.config.logger import setup_logger
from app.schemas.scraper import Account
from app.config.config import WEBDRIVER_WAIT_TIMEOUT
from app.utils.colors import Color

logger = setup_logger(__name__)

class Driver:
    def __enter__(self, wait = WEBDRIVER_WAIT_TIMEOUT['short']) -> Tuple[Chrome, WebDriverWait]:
        # Setup the Chrome options.
        options = ChromeOptions()

        # Enable the Chrome browser cloud management making it easier to download.
        options.add_argument('--enable-chrome-browser-cloud-management')

        # Disable the sandbox to prevent the browser from crashing.
        options.add_argument('--disable-sandbox')

        # Makes the browser wait for the page to load completely.
        options.page_load_strategy = 'normal'

        options.add_experimental_option('prefs', {
            # Change the default download directory.
            'download.default_directory': None,

            # Disable the prompt for download.
            'download.prompt_for_download': False,

            # Enable the download directory upgrade.
            'download.directory_upgrade': True,

            # Make sure that the browser always opens the PDF files externally.
            'plugin.always_open_pdf_externally': True
        })

        # Setup the Chrome driver.
        self.driver = Chrome(options=options)
        self.wait = WebDriverWait(self.driver, wait)

        return self.driver, self.wait

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.driver.quit()
        if exc_type is not None:
            logger.error(f'An error occurred: {exc_value}')
            logger.error(f'Traceback (most recent call last):\n {traceback}')

class Scraper:

    def authenticate_vbs(self, account: Account) -> bool:
        """
            Authenticates whether the account for VBS is valid
            or not by logging into the VBS website.

            Parameters:
                account (Account): username and password for the VBS account.

            Returns:
                bool: True if the account is valid, False otherwise.
        """

        url = 'https://ictsi.vbs.1-stop.biz'

        with Driver() as (driver, wait):

            try:
                driver.get(url)
                # Wait for the page to load and then login.
                wait.until(EC.all_of(
                        EC.visibility_of_element_located((By.ID, 'USERNAME')),
                        EC.visibility_of_element_located((By.ID, 'PASSWORD'))
                    )
                )

                driver.find_element(By.ID, 'USERNAME').send_keys(account.username)
                driver.find_element(By.ID, 'PASSWORD').send_keys(account.password.get_secret_value())
                driver.find_element(By.ID, 'form1').submit()

                # Check for login failure.
                if 'Login' in driver.page_source:
                    try:
                        wait.until(EC.visibility_of_element_located((By.ID, 'msgHolder')))
                        logger.error(f'Invalid {Color.colorize("VBS", Color.BOLD)} account. Please try again.')
                        return False
                    except TimeoutException:
                        logger.info(f'Successfully logged in {Color.colorize("VBS", Color.BOLD)} account.')
                        return True
                    except NoSuchElementException:
                        logger.info(f'Successfully logged in {Color.colorize("VBS", Color.BOLD)} account.')
                        return True
                else:
                    logger.info(f'Successfully logged in {Color.colorize("VBS", Color.BOLD)} account.')
                    return True

            except TimeoutException:
                logger.error('Timed out. The page took too long to load.')
                return False

    def authenticate_intercommerce(self, account: Account) -> bool:
        """
            Authenticates whether the account for InterCommerce is valid
            or not by logging into the InterCommerce website.

            Parameters:
                account (Account): username and password for the InterCommerce account.

            Returns:
                bool: True if the account is valid, False otherwise.
        """

        url = 'https://www.intercommerce.com.ph/'

        with Driver() as (driver, wait):

            try:
                driver.get(url)
                # Wait for the page to load and then login.
                wait.until(EC.all_of(
                        EC.visibility_of_element_located((By.NAME, 'clientid')),
                        EC.visibility_of_element_located((By.NAME, 'password'))
                    )
                )

                driver.find_element(By.NAME, 'clientid').send_keys(account.username)
                driver.find_element(By.NAME, 'password').send_keys(account.password.get_secret_value())
                driver.find_element(By.NAME, 'form1').submit()

                # Check for login failure.
                if 'Incorrect Password' in driver.page_source:
                    try:
                        wait.until(EC.visibility_of_element_located((By.NAME, 'frmCreate')))
                        logger.error(f'Invalid {Color.colorize("InterCommerce", Color.BOLD)} account. Please try again.')
                        return False
                    except TimeoutException:
                        logger.info(f'Successfully logged in {Color.colorize("InterCommerce", Color.BOLD)} account.')
                        return True
                    except NoSuchElementException:
                        logger.info(f'Successfully logged in {Color.colorize("InterCommerce", Color.BOLD)} account.')
                        return True
                else:
                    logger.info(f'Successfully logged in {Color.colorize("InterCommerce", Color.BOLD)} account.')
                    return True

            except TimeoutException:
                logger.error('Timed out. The page took too long to load.')
                return False