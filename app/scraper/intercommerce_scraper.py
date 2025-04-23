from selenium.webdriver import Chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from app.utils.colors import Color
from app.config.settings import Settings
from app.config.logger import setup_logger
from app.utils.cache.row_cache import (
    cache_row,
    remove_row_from_csv,
    get_reference_numbers,
    check_scraped
)
from app.utils.directory import (
    create_save_directory
)
from app.models.scraper import (
    Account,
    Dates,
    Row
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

    def _get_row_data(self, row_id: int,save_dir: str, wait: WebDriverWait) -> Row:
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
        cache_row([row_data], save_dir)

        return row_data

    def _crawl_rows(self, dates: Dates, branch: str, save_dir: str, driver: Chrome, wait: WebDriverWait) -> None:
        """
        Crawl the Intercommerce database to retrieve data based on the provided dates.
        All the row datas are stored in a CSV file so that we can process all the documents
        later on after the crawling is done.

        Parameters:
            dates (Dates): The Dates object containing the start and end dates.
            branch (str): The branch to crawl the database from.
            driver (Chrome): The Selenium WebDriver instance.
            wait (WebDriverWait): The WebDriverWait instance for waiting for elements.
        """
        offset = 0

        while True:
            self._load_page(branch, offset, driver, wait)

            # Wait for the row to have a date past the end date.
            if not self._process_rows(dates, save_dir, driver, wait):
                logger.info('Finished crawling the database. All rows have been cached.')
                break

            offset += 10

    def _load_page(self, branch: str, offset: int, driver: Chrome, wait: WebDriverWait) -> None:
        """
        Load the Intercommerce page with the specified branch and offset.

        Parameters:
            branch (str): The branch to load the page from.
            offset (int): The offset to use for pagination.
            driver (Chrome): The Selenium WebDriver instance.
            wait (WebDriverWait): The WebDriverWait instance for waiting for elements.
        """
        url = Settings().INTERCOMMERCE_URLS[branch] + str(offset)
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.NAME, 'txtClient')))

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
                row = self._get_row_data(row_id, save_dir, wait)

                if dates.end_date < row.creation_date < dates.start_date or row.status != 'AG':
                    raise InvalidDocumentException('The document is not valid.')

                if dates.start_date > row.creation_date:
                    remove_row_from_csv('rows.csv', save_dir, row.reference_number)
                    return False

            except (InvalidDocumentException, CachedException):
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
            self._crawl_rows(dates, branch, save_dir, driver, wait)

        except TimeoutException:
            logger.error('Timed out. The Intercommerce database page did not load.')
            raise LoadingFailedException('Timed out. The Intercommerce database page did not load.')