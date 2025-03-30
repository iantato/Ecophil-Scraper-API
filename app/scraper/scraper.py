import shutil
from os import path
from typing import Tuple

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from app.utils.colors import Color
from app.schemas.scraper import Account, Dates
from app.config.logger import setup_logger
from app.utils.directory import wait_for_download, check_directory, create_save_directory
from app.config.config import WEBDRIVER_WAIT_TIMEOUT, DATA_DIR

logger = setup_logger(__name__)

class Driver:

    def __init__(self, wait = WEBDRIVER_WAIT_TIMEOUT['short']) -> None:
        self.wait_timeout = wait

    def __enter__(self) -> Tuple[Chrome, WebDriverWait]:
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
            'download.default_directory': DATA_DIR,

            # Disable the prompt for download.
            'download.prompt_for_download': False,

            # Enable the download directory upgrade.
            'download.directory_upgrade': True,

            # Make sure that the browser always opens the PDF files externally.
            'plugin.always_open_pdf_externally': True
        })

        # Setup the Chrome driver.
        self.driver = Chrome(options=options)
        self.wait = WebDriverWait(self.driver, self.wait_timeout)

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

    def move_ati(self, filename: str, to_directory: str) -> None:
        """
            Moves the Asian Terminal Inc. (ATI) data file to the
            specific documents' directory.

            Parameters:
                filename (str): the name of the file.
                to_directory (str): the name of the directory to which to move the file.
        """

        if not check_directory(path.join(DATA_DIR, to_directory)):
            logger.error(f'An error occured on moving the {Color.colorize("ATI.CSV", Color.BOLD)} file.')
            create_save_directory(to_directory)

        src = path.join(DATA_DIR, filename)
        dst = path.normpath(f'{DATA_DIR}/documents/{to_directory}/cache/ati.csv')

        shutil.move(src, dst)
        logger.info(f'Moved file: [{Color.colorize(filename, Color.CYAN)}] to directory: [{Color.colorize(to_directory, Color.CYAN)}].')

    def download_ati(self, account: Account, dates: Dates) -> None:
        """
            Downloads the Asian Terminal Inc. (ATI) data from the VBS website.
            The data is downloaded in CSV format and saved in the
            specified directory.

            Parameters:
                account (Account): username and password for the VBS account.
                dates (Dates): start and end date for the data to be downloaded.
        """

        url = 'https://ictsi.vbs.1-stop.biz'
        save_dir = f'{dates.start_date.strftime("%b %d %Y")} - {dates.end_date.strftime("%b %d %Y")}'

        with Driver() as (driver, wait):
            try:
                # Login to the VBS website.
                driver.get(url)
                logger.info(f'Logging in to {Color.colorize("Intercommerce", Color.BOLD)} account and downloading {Color.colorize("ATI", Color.BOLD)} data.')
                # Wait for the page to load and then login.
                wait.until(EC.all_of(
                        EC.visibility_of_element_located((By.ID, 'USERNAME')),
                        EC.visibility_of_element_located((By.ID, 'PASSWORD'))
                    )
                )
                driver.find_element(By.ID, 'USERNAME').send_keys(account.username)
                driver.find_element(By.ID, 'PASSWORD').send_keys(account.password.get_secret_value())
                driver.find_element(By.ID, 'form1').submit()

                # Wait for the page to load and then go to the terms and conditions page.
                wait.until(EC.presence_of_element_located((By.ID, 'vbs_new_selected_facilityid')))
                # Accept the terms and conditions.
                driver.get('https://atimnl.vbs.1-stop.biz/Default.aspx?vbs_Facility_Changed=true&vbs_new_selected_FACILITYID=ATIMNL')
                wait.until(EC.element_to_be_clickable((By.ID, 'Accept'))).click()

                # Wait for the page to load and then go to the transactions page.
                wait.until(EC.presence_of_element_located((By.ID, 'NotifyMessages')))
                driver.get('https://atimnl.vbs.1-stop.biz/PointsTransactions.aspx')

                # Change the dates in the form.
                # Date from.
                element = wait.until(EC.element_to_be_clickable((By.ID, 'PointsTransactionsSearchForm___DATEFROM')))
                driver.execute_script('arguments[0].removeAttribute("readonly")',
                                      element)
                element.clear()
                element.send_keys(f'{dates.start_date.day}/{dates.start_date.month}/{dates.start_date.year}')

                # Date to.
                element = wait.until(EC.element_to_be_clickable((By.ID, 'PointsTransactionsSearchForm___DATETO')))
                driver.execute_script('arguments[0].removeAttribute("readonly")',
                                      element)
                element.clear()
                element.send_keys(f'{dates.end_date.day}/{dates.end_date.month}/{dates.end_date.year}')

                # Request for the data from the database.
                driver.find_element(By.ID, 'PointsTransactionsSearchForm___REFERENCE').click()
                driver.find_element(By.ID, 'Search').click()

                # We change the web driver wait timeout to 120 seconds
                # because the data might take a while to load. This is the
                # button for downloading the cvs file itself.
                element = WebDriverWait(driver, 120).until(
                    EC.element_to_be_clickable((By.ID, 'CSV'))
                )
                element.click()

                if wait_for_download('PointsTransactions.csv'):
                   self.move_ati('PointsTransactions.csv', save_dir)

            except TimeoutException as e:
                logger.error('Timed out. The page took too long to load.')
                logger.error('Stacktrace:', e)

    def move_mictsi(self, filename: str, to_directory: str) -> None:
        """
            Moves the Manila International Container Terminal Servirces, Inc. (MICTSI) data file to the
            specific documents' directory.

            Parameters:
                filename (str): the name of the file.
                to_directory (str): the name of the directory to which to move the file.
        """

        if not check_directory(path.join(DATA_DIR, to_directory)):
            logger.error(f'An error occured on moving the {Color.colorize("MICTSI.CSV", Color.BOLD)} file.')
            create_save_directory(to_directory)

        src = path.join(DATA_DIR, filename)
        dst = path.normpath(f'{DATA_DIR}/documents/{to_directory}/cache/mictsi.csv')

        shutil.move(src, dst)
        logger.info(f'Moved file: [{Color.colorize(filename, Color.CYAN)}] to directory: [{Color.colorize(to_directory, Color.CYAN)}].')

    def download_mictsi(self, account: Account, dates: Dates) -> None:
        """
            Downloads the Manila International Container Terminal Servirces, Inc. (MICTSI) data from the InterCommerce website.
            The data is downloaded in CSV format and saved in the
            specified directory.

            Parameters:
                account (Account): username and password for the InterCommerce account.
                dates (Dates): start and end date for the data to be downloaded.
        """

        url = 'https://ictsi.vbs.1-stop.biz'
        save_dir = f'{dates.start_date.strftime("%b %d %Y")} - {dates.end_date.strftime("%b %d %Y")}'

        with Driver() as (driver, wait):
            try:
                # Login to the VBS website.
                driver.get(url)
                logger.info(f'Logging in to {Color.colorize("Intercommerce", Color.BOLD)} account and downloading {Color.colorize("MICTSI", Color.BOLD)} data.')

                # Wait for the page to load and then login.
                wait.until(EC.all_of(
                        EC.visibility_of_element_located((By.NAME, 'USERNAME')),
                        EC.visibility_of_element_located((By.NAME, 'PASSWORD'))
                    )
                )
                driver.find_element(By.ID, 'USERNAME').send_keys(account.username)
                driver.find_element(By.ID, 'PASSWORD').send_keys(account.password.get_secret_value())
                driver.find_element(By.ID, 'form1').submit()

                # Wait for the page to load and then go to the terms and conditions page.
                wait.until(EC.presence_of_element_located((By.ID, 'vbs_new_selected_facilityid')))
                # Wait for the page to load and then go to the terms and conditions page.
                driver.get('https://ictsi.vbs.1-stop.biz/Default.aspx?vbs_Facility_Changed=true&vbs_new_selected_FACILITYID=ICTSI')
                wait.until(EC.element_to_be_clickable((By.ID, 'Accept'))).click()

                # Wait for the page to load and then go to the transactions page.
                wait.until(EC.presence_of_element_located((By.ID, 'NotifyMessages')))
                driver.get('https://ictsi.vbs.1-stop.biz/PointsTransactions.aspx')

                # Change the dates in the form.
                # Date from.
                element = wait.until(EC.element_to_be_clickable((By.ID, 'PointsTransactionsSearchForm___DATEFROM')))
                driver.execute_script('arguments[0].removeAttribute("readonly")',
                                      element)
                element.clear()
                element.send_keys(f'{dates.start_date.day}/{dates.start_date.month}/{dates.start_date.year}')

                # Date to.
                element = wait.until(EC.element_to_be_clickable((By.ID, 'PointsTransactionsSearchForm___DATETO')))
                driver.execute_script('arguments[0].removeAttribute("readonly")',
                                      element)
                element.clear()
                element.send_keys(f'{dates.end_date.day}/{dates.end_date.month}/{dates.end_date.year}')

                # Request for the data from the database.
                driver.find_element(By.ID, 'PointsTransactionsSearchForm___REFERENCE').click()
                driver.find_element(By.ID, 'Search').click()

                # We change the web driver wait timeout to 120 seconds
                # because the data might take a while to load. This is the
                # button for downloading the cvs file itself.
                element = WebDriverWait(driver, 120).until(
                    EC.element_to_be_clickable((By.ID, 'CSV'))
                )
                element.click()

                if wait_for_download('PointsTransactions.csv'):
                   self.move_mictsi('PointsTransactions.csv', save_dir)

            except TimeoutException as e:
                logger.error('Timed out. The page took too long to load.')
                logger.error('Stacktrace:', e)