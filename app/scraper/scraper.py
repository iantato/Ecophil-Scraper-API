import time
import shutil
from os import path
from typing import Tuple

import polars as pl
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from app.utils.colors import Color
from app.models.scraper import Account, Dates
from app.config.logger import setup_logger
from app.utils.directory import (
        wait_for_download,
        check_directory,
        create_save_directory,
        check_file
    )
from app.config.settings import Settings
from app.config.constants import WEBDRIVER_WAIT_TIMEOUT, DATA_DIR
from app.models.scraper import Row, Document
from app.utils.exceptions import (
        LoginFailedException,
        LoadingFailedException,
        InvalidDocumentException
    )

logger = setup_logger(__name__)

class Driver:
    def __init__(self, wait=WEBDRIVER_WAIT_TIMEOUT['short'], download_dir=DATA_DIR) -> None:
        self.wait_timeout = wait
        self.download_dir = download_dir

    def __enter__(self) -> Tuple[Chrome, WebDriverWait]:

        # Setup the Chrome options.
        options = ChromeOptions()

        # Add headless mode option for background operation
        # options.add_argument('--headless=new')  # Uncomment when ready

        options.add_argument('--enable-chrome-browser-cloud-management')

        # Disable the sandbox to prevent the browser from crashing.
        options.add_argument('--disable-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.page_load_strategy = 'normal'

        options.add_experimental_option('prefs', {
            'download.default_directory': self.download_dir,
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
        if hasattr(self, 'driver'):
            self.driver.quit()

        if exc_type is not None:
            logger.error(f'An error occured: {exc_value}')

class Scraper:

    def _verify_vbs_login(self, driver: Chrome, wait: WebDriverWait) -> bool:
        """
            Verifies whether the login to the VBS website was successful
            or not by checking if the login error message is present and
            checking whether the login page is still present.

            Parameters:
                driver (Driver): the web driver.
                wait (WebDriverWait): the web driver wait.

            Returns:
                bool: True if the login was successful, False otherwise.
        """

        try:
            wait.until(EC.presence_of_element_located((By.ID, 'msgHolder')))
            return False
        except TimeoutException or NoSuchElementException:
            return 'Login' not in driver.page_source

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

                # Verify if the login is successful.
                login_successful = self._verify_vbs_login(wait)
                if login_successful:
                    logger.info(f'Successfully logged in {Color.colorize("VBS", Color.BOLD)} account.')
                    return True

                # Raises LoginFailedException if the login is not successful.
                raise LoginFailedException('Login failed. Please check your username and password.')

            except TimeoutException:
                logger.error('Timed out. The page took too long to load.')
                raise LoadingFailedException('Timed out. The page took too long to load.')

    def _verify_intercommerce_login(self, driver: Chrome, wait: WebDriverWait) -> bool:
        """
            Verifies whether the login to the InterCommerce website was successful
            or not by checking if the login error message is present and
            checking whether the login page is still present.

            Parameters:
                driver (Driver): the web driver.
                wait (WebDriverWait): the web driver wait.

            Returns:
                bool: True if the login was successful, False otherwise.
        """

        try:
            wait.until(EC.presence_of_element_located((By.NAME, 'frmCreate')))
            return False
        except TimeoutException or NoSuchElementException:
            return 'Incorrect Password' not in driver.page_source


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

                # Verify if the login is successful.
                login_successful = self._verify_intercommerce_login(driver, wait)
                if login_successful:
                    logger.info(f'Successfully logged in {Color.colorize("InterCommerce", Color.BOLD)} account.')
                    return True

                # Raises LoginFailedException if the login is not successful.
                raise LoginFailedException('Login failed. Please check your username and password.')

            except TimeoutException:
                logger.error('Timed out. The page took too long to load.')
                raise LoadingFailedException('Timed out. The page took too long to load.')

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

        save_dir = f'{dates.start_date.strftime("%b %d %Y")} - {dates.end_date.strftime("%b %d %Y")}'
        url = 'https://ictsi.vbs.1-stop.biz'

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
                # button for downloading the csv file itself.
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

        save_dir = f'{dates.start_date.strftime("%b %d %Y")} - {dates.end_date.strftime("%b %d %Y")}'
        url = 'https://ictsi.vbs.1-stop.biz'

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

            except TimeoutException:
                logger.error('Timed out. The page took too long to load.')

    def _get_container_number_from_pdf(self, reference_no: str, driver: Chrome, filename: Optional[str]) -> str:
        """
            Extracts the container number from a PDF file.
            The PDF file is downloaded from the InterCommerce website.

            Parameters:
                reference_no (str): The reference number of the document.
                driver (Driver): The web driver.
                filename (str): The name of the PDF file.

            Returns:
                str: The extracted container number.
        """

        url = f'https://www.intercommerce.com.ph/WebCWS/pdf/sadPEZAEXP.php?aplid={reference_no}'
        driver.get(url)

        try:
            if wait_for_download('doc.pdf'):
                 with open(f'{DATA_DIR}/{filename}', 'rb') as file:
                    reader = PdfReader(file, strict=False)
                    logger.info(f'Extracting container number from PDF for [{Color.colorize(reference_no, Color.CYAN)}].')
                    texts = reader.pages[0].extract_text().replace('- Container No(s) -', '').split('\n')

                    for text in texts:
                        if 'Container No' in text:
                            container_number = text.rsplit(' ', 1)[1].strip()
                            logger.info(f'Container number extracted successfully for [{Color.colorize(reference_no, Color.CYAN)}].')
                            return container_number

            # If the PDF file is not downloaded, raise an exception.
            raise InvalidDocumentException(f'{reference_no} document is unprocessable. It is invalid')

        finally:
            remove(f'{DATA_DIR}/{filename}')

    def crawl_database(self, account: Account, dates: Dates, branch: str) -> None:

        url = 'https://www.intercommerce.com.ph/'

        with Driver() as (driver, wait):
            try:
                # Login to the Intercommerce website.
                driver.get(url)
                logger.info(f'Logging in to {Color.colorize("Intercommerce", Color.BOLD)} account.')

                wait.until(EC.all_of(
                        EC.visibility_of_element_located((By.NAME, 'clientid')),
                        EC.visibility_of_element_located((By.NAME, 'password'))
                    )
                )
                driver.find_element(By.NAME, 'clientid').send_keys(account.username)
                driver.find_element(By.NAME, 'password').send_keys(account.password.get_secret_value())
                driver.find_element(By.NAME, 'form1').submit()
                logger.info('Logged in successfully.')

                # Wait for the page to load and then go to the data page.
                wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'toplink')))
                time.sleep(2) # ⚠️ This is a temporary fix. Our code is too fast hence. ⚠️

                # Start craping the documents from the Intercommerce database.
                page_offset = 0

                for row_id in range(15, 18):
                    driver.get(Settings().INTERCOMMERCE_URLS[branch] + str(page_offset))
                    try:
                        print('test 2')
                        # Get the row data from the table in the page.
                        row_xpath = f'/html/body/form/table/tbody/tr[9]/td[2]/table/tbody/tr/td/div/table/tbody/tr/td/table/tbody/tr[{row_id}]'
                        row = wait.until(EC.presence_of_element_located((By.XPATH, row_xpath))).find_elements(By.XPATH, './*')
                        row_data = Row.from_array(
                            [child.text for child in row]
                        )

                        # Skip the document if it is not in the date range or if the status is not 'AG'.
                        if (dates.end_date < row_data.creation_date < dates.start_date) or row_data.status != 'AG':
                            raise InvalidDocumentException(f'{row_data.reference_number} document is unprocessable. It is invalid')

                        # Stop scraping if the current dates are out of range.
                        if dates.end_date > row_data.creation_date:
                            logger.info('Scraping stopped. The date is out of range.')
                            return

                        # Scrape the document in the current row.
                        self.scrape_document(driver, wait, row_data)

                    except InvalidDocumentException:
                        logger.error(f'Skipped document [{Color.colorize(row_data.reference_number, Color.CYAN)}].')
                        driver.get(Settings().INTERCOMMERCE_URLS[branch] + str(page_offset))
                        continue

            except TimeoutException:
                logger.error('Timed out. The page took too long to load.')
                raise LoadingFailedException('Timed out. The page took too long to load.')

    def _get_release_table(self, wait: WebDriverWait) -> str:
        table_xpath = '/html/body/form/table/tbody/tr[8]/td[2]'
        try:
            table = wait.until(EC.presence_of_element_located((By.XPATH, table_xpath))).find_elements(By.TAG_NAME, 'td')
            data = [child.text for child in table]

            if "Released" in data or "Transferred" in data:
                return "Released"
            elif "Approved" in data:
                return "Approved"
            else:
                return None

        except TimeoutException:
            raise InvalidDocumentException('Timed out. There are no release table in the document.')

    def scrape_document(self, driver: Chrome, wait: WebDriverWait, row_data: Row) -> None:

        url = f'https://www.intercommerce.com.ph/WebCWS/cws_ip_step2PEZAEXPexpress.asp?ApplNo={row_data.reference_number}'
        driver.get(url)
        logger.info(f'Scraping document [{Color.colorize(row_data.reference_number, Color.CYAN)}].')

        if 'The page cannot be displayed because an internal server error has occurred.' in driver.page_source:
            logger.error(f'An error occurred while scraping the document [{Color.colorize(row_data.reference_number, Color.CYAN)}].')
            raise InvalidDocumentException(f'{row_data.reference_number} document is unprocessable. It is invalid')

        try:
            document = Document(
                invoice_number=wait.until(EC.presence_of_element_located((By.NAME, 'txtInvNo'))).get_attribute('value'),
                container_type=wait.until(EC.presence_of_element_located((By.NAME, 'txtTotContType'))).get_attribute('value'),
                quantity=wait.until(EC.presence_of_element_located((By.NAME, 'txtPackages'))).get_attribute('value')
            )

            status = self._get_release_table(driver, wait)
            if not status and document.container_type == 'FCL':
                pass


        except TimeoutException or NoSuchElementException:
            logger.error(f'An error occurred while scraping the document [{Color.colorize(row_data.reference_number, Color.CYAN)}].')
            raise InvalidDocumentException(f'{row_data.reference_number} document is unprocessable. It is invalid')