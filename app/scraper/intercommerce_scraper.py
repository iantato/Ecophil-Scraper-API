from os import path
from typing import Optional

import polars as pl
from polars import Series
from PyPDF2 import PdfReader
from selenium.webdriver import Chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from app.utils.colors import Color
from app.config.settings import Settings
from config.constants import DATA_DIR
from app.config.logger import setup_logger
from app.utils.cache.row_cache import (
    cache_row,
    remove_row_from_csv,
    get_reference_numbers,
    check_scraped
)
from app.utils.directory import (
    create_save_directory,
    wait_for_download
)
from app.models.scraper import (
    Account,
    Dates,
    Row,
    Document
)
from app.utils.exceptions import (
    LoginFailedException,
    LoadingFailedException,
    InvalidDocumentException,
    CachedException
)

logger = setup_logger(__name__)

class IntercommerceScraper:

    def __init__(self):
        self.url = 'https://www.intercommerce.com.ph/'

    def _verify_login(self, driver: Chrome, wait: WebDriverWait) -> bool:
        """
        Verify if the login was successful by checking for the presence of specific elements.
        This method checks for the presence of an error message element that indicates a failed login.

        Parameters:
            driver (Chrome): The Selenium WebDriver instance.
            wait (WebDriverWait): The WebDriverWait instance for waiting for elements.

        Returns:
            bool: True if login was successful, False otherwise.
        """
        try:
            wait.until(EC.presence_of_element_located((By.NAME, 'frmCreate')))
            return False
        except TimeoutException or NoSuchElementException:
            return 'Incorrect Password' not in driver.page_source

    def _authenticate(self, account: Account, driver: Chrome, wait: WebDriverWait) -> None:
        """
        Authenticate the user with the Intercommerce system using the provided credentials.
        This method uses the Selenium WebDriver to interact with the Intercommerce login page.
        It waits for the page to load and checks for the presence of specific elements
        to determine if the login was successful.

        Parameters:
            account (Account): The account object containing the username and password.

        Returns:
            bool: True if login was successful, False otherwise.

        Raises:
            LoginFailedException: If the login was unsuccessful.
            LoadingFailedException: If the login page did not load within the specified time.
        """
        try:
            driver.get(self.url)
            # Wait for the login page to load.
            wait.until(EC.all_of(
                    EC.visibility_of_element_located((By.NAME, 'clientid')),
                    EC.visibility_of_element_located((By.NAME, 'password'))
                )
            )

            driver.find_element(By.NAME, 'clientid').send_keys(account.username)
            driver.find_element(By.NAME, 'password').send_keys(account.password.get_secret_value())
            driver.find_element(By.NAME, 'form1').submit()

            # Raises LoginFailedException if login was unsuccessful.
            if not self._verify_login(driver, wait):
                raise LoginFailedException("Login to Intercommerce failed. Please check your credentials.")

            logger.info('Successfully logged in to Intercommerce account.')

        except TimeoutException or NoSuchElementException:
            logger.error('Timed out. The Intercommerce login page did not load.')
            raise LoadingFailedException('Timed out. The Intercommerce login page did not load.')

    def _generate_save_directory(self, dates: Dates) -> str:
        """
        Generate a save directory based on the start and end dates provided.
        The directory name is formatted as "MMM DD YYYY - MMM DD YYYY".

        Parameters:
            dates (Dates): The Dates object containing the start and end dates.

        Returns:
            str: The formatted save directory name.
        """
        save_dir = f'{dates.start_date.strftime("%b %d %Y")} - {dates.end_date.strftime("%b %d %Y")}'

        create_save_directory(save_dir)

        logger.info('Save directory initialized')
        return save_dir

    def _get_row_data(self, row_id: int, wait: WebDriverWait) -> Row:
        """
        Get the row data from the Intercommerce system.
        It stores the row data in a CSV file for later use.

        Parameters:
            row_id (int): The ID of the row to retrieve.
            driver (Chrome): The Selenium WebDriver instance.
            wait (WebDriverWait): The WebDriverWait instance for waiting for elements.
            save_dir (str): The directory where the cached rows are stored.

        Returns:
            Row: The row data retrieved from the Intercommerce system.
        """
        row_xpath = f'/html/body/form/table/tbody/tr[9]/td[2]/table/tbody/tr/td/div/table/tbody/tr/td/table/tbody/tr[{row_id}]'
        row = wait.until(EC.presence_of_element_located((By.XPATH, row_xpath))).find_elements(By.XPATH, './*')
        row_data = Row.from_array([child.text for child in row])

        return row_data

    def _process_rows(self, dates: Dates, save_dir: str, driver: Chrome, wait: WebDriverWait) -> bool:
        """
        Process the rows in the Intercommerce database to check if they are valid.
        This method checks if the rows are valid based on the provided dates and status.
        If a row is invalid, it raises an InvalidDocumentException. If the row is already cached,
        it raises a CachedException.
        If the row is valid, it caches the row data and returns True.

        Parameters:
            dates (Dates): The Dates object containing the start and end dates.
            save_dir (str): The directory where the cached rows are stored.
            driver (Chrome): The Selenium WebDriver instance.
            wait (WebDriverWait): The WebDriverWait instance for waiting for elements.

        Returns:
            bool: True if the row is valid, False if the end date is reached.
        """
        for row_id in range(15, 25):
            try:
                row = self._get_row_data(row_id, wait)

                if dates.end_date < row.creation_date or row.status != 'AG':
                    raise InvalidDocumentException('The document is not valid.')

                if dates.start_date > row.creaton_date:
                    return False

                # Cache the row data if it is valid.
                cache_row([row], save_dir)

            except (InvalidDocumentException, CachedException, ValueError):
                logger.warning(f'Invalid Document. Skipping document [{Color.colorize(row.reference_number, Color.CYAN)}].')
                continue

        return True

    def crawl_database(self, account: Account, dates: Dates, branch: str,
                       driver: Chrome, wait: WebDriverWait) -> None:
        """
        Crawl the Intercommerce database to retrieve data based on the provided dates.
        All the row datas are stored in a CSV file so that we can process all the documents
        later on after the crawling is done.

        Parameters:
            account (Account): The account object containing the username and password.
            dates (Dates): The Dates object containing the start and end dates.
            branch (str): The branch to crawl the database from.
            driver (Chrome): The Selenium WebDriver instance.
            wait (WebDriverWait): The WebDriverWait instance for waiting for elements.
        """

        save_dir = self._generate_save_directory(dates)

        try:
            # Authenticate the user with the Intercommerce system.
            self._authenticate(account, driver, wait)

            # Crawl the Intercommerce database to retrieve data based on the provided dates.
            offset = 0

            while True:

                # Load the Intercommerce database page.
                url = Settings().INTERCOMMERCE_URLS[branch] + str(offset)
                driver.get(url)
                wait.until(EC.presence_of_element_located((By.NAME, 'txtClient')))

                # Wait for the row to have a date past the end date.
                if not self._process_rows(dates, save_dir, driver, wait):
                    logger.info('Finished crawling the database. All rows have been cached.')
                    break

                offset += 10

        except TimeoutException:
            logger.error('Timed out. The Intercommerce database page did not load.')
            raise LoadingFailedException('Timed out. The Intercommerce database page did not load.')

    def _handle_fcl(self, row_data: Row, document_data: Document, filename: str, driver: Chrome, wait: WebDriverWait) -> None:
        container_number = self._get_container_number_from_pdf(filename)

    def _get_date_from_container_number(container_number: str, filename: Optional[str], directory: Optional[str]) -> Series:
        '''
        Retrieves the release date of a container from a CSV file.

        Parameters:
            container_number (str): The container number to search for.
            filename (str): The name of the CSV file to read.
            directory (str): The directory where the CSV file is located.

        Raises:
            InvalidDocumentException: If the container number is not found in the CSV file.

        Returns:
            pl.Series: A Polars Series containing the event dates for the specified container number.
        '''

        # Turns the 'Event Date' into a datetime object and then
        # filters the dataframe to only include the specified container
        #  number and the 'ARRIVE' event type.
        q = (
            pl.scan_csv(path.join(directory, filename))
            .with_columns(pl.col('Event Date').str.to_datetime('%d-%b-%y %H:%M'))
            .filter((pl.col('Container') == container_number) & (pl.col('Point Event') == 'ARRIVE'))
            .collect()
        )

        if q.is_empty():
            logger.warning(f"{Color.colorize(container_number, Color.BOLD)} not found in {filename}.")
            raise InvalidDocumentException(f"Container number {container_number} not found in {filename}.")

        return q.get_column('Event Date')

    def _download_document_pdf(self, reference_number: str, driver: Chrome, wait: WebDriverWait) -> None:
        """
        Downloads the document PDF from the Intercommerce system using the provided reference number.

        Parameters:
            reference_number (str): The reference number of the document to download.
            driver (Chrome): The Selenium WebDriver instance.
            wait (WebDriverWait): The WebDriverWait instance for waiting for elements.

        Raises:
            InvalidDocumentException: If the document is unprocessable or invalid.
        """
        url = f'{self.url}/WebCWS/pdf/sadPEZAEXP.php?aplid={reference_number}'
        driver.get(url)

        if 'The page cannot be displayed because an internal server error has occurred.' in driver.page_source:
            raise InvalidDocumentException(f'{reference_number} document is unprocessable. It is invalid')

    def _get_container_number_from_pdf(self, filename: str) -> str:
        """
        Extracts the container number from the downloaded PDF file.

        Parameters:
            filename (str): The name of the PDF file to extract the container number from.

        Returns:
            str: The extracted container number.
        """

        if wait_for_download(filename):
            with open(path.join(DATA_DIR, filename), 'rb') as pdf:
                reader = PdfReader(pdf, strict=False)
                texts = reader.pages[0].extract_text().replace('- Container No(s) -', '').split('\n')

                for text in texts:
                    if 'Container No' in text:
                        container_number = text.rsplit(' ', 1)[1].strip()
                        return container_number

    def _process_documents(self, save_dir: str, dates: Dates, driver: Chrome, wait: WebDriverWait) -> None:

        for reference in get_reference_numbers('rows.csv', save_dir):
            try:
                url = f'{self.url}/WebCWS/cws_ip_step2PEZAEXPexpress.asp?ApplNo={reference}'
                driver.get(url)

                if 'The page cannot be displayed because an internal server error has occurred.' in driver.page_source:
                    raise InvalidDocumentException(f'{reference} document is unprocessable. It is invalid')

                scraped = check_scraped(reference, 'rows.csv', save_dir)
                if scraped:
                    raise CachedException(f'{reference} document is already cached.')

                status = self._get_release_status(driver, wait)
                document = self._get_document_data(driver, wait)
                if status != 'Released' and document.container_type == 'FCL':
                    pass

            except (InvalidDocumentException, CachedException):
                logger.warning(f'Skipping... An error occurred while scraping the document [{Color.colorize(reference, Color.CYAN)}].')
                remove_row_from_csv('rows.csv', save_dir, reference)
                continue

    def _get_release_status(self, driver: Chrome, wait: WebDriverWait) -> None:
        """
        Gets the release table from the document page.
        The release table contains the status of the document.

        Parameters:
            driver (Chrome): The Selenium WebDriver instance.
            wait (WebDriverWait): The WebDriverWait instance for waiting for elements.

        Returns:
            str: The status of the document. It can be 'Released', 'Approved', or None.
        """
        table_xpath = '/html/body/form/table/tbody/tr[8]/td[2]'

        try:
            table = wait.until(EC.presence_of_element_located((By.XPATH, table_xpath))).find_elements(By.TAG_NAME, 'td')
            data = [child.text for child in table]

            if 'Released' in data or 'Transferred' in data:
                return 'Released'
            elif 'Approved' or 'Auto-Inspected' in data:
                return 'Approved'
            else:
                return None

        except TimeoutException or NoSuchElementException:
            raise InvalidDocumentException('Timed out. There are no release table in the document.')

    def _get_document_data(self, driver: Chrome, wait: WebDriverWait) -> Document:
        """
        Gets the document data from the document page.
        The document data contains the invoice number, container type, and quantity.

        Parameters:
            driver (Chrome): The Selenium WebDriver instance.
            wait (WebDriverWait): The WebDriverWait instance for waiting for elements.

        Returns:
            Document: The document data containing the invoice number, container type, and quantity.
        """
        try:

            document = Document(
                invoice_number=wait.until(EC.presence_of_element_located((By.NAME, 'txtInvNo'))).get_attribute('value'),
                container_type=wait.until(EC.presence_of_element_located((By.NAME, 'txtTotContType'))).get_attribute('value'),
                quantity=wait.until(EC.presence_of_element_located((By.NAME, 'txtPackages'))).get_attribute('value')
            )

            return document

        except TimeoutException or NoSuchElementException:
            raise InvalidDocumentException('Timed out. There are no document data in the document.')