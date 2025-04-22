from time import sleep

from selenium.webdriver import Chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from app.utils.colors import Color
from app.scraper.driver import Driver
from app.config.settings import Settings
from app.config.logger import setup_logger
from app.utils.cache.row_cache import cache_row, remove_row_from_csv
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

    def authenticate(self, account: Account) -> bool:
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
        with Driver() as (driver, wait):
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

                # Verify if the login is successful.
                login_successful = self._verify_login(driver, wait)
                if login_successful:
                    logger.info("Login was successful in Intercommerce Account.")
                    return True

                # Raises LoginFailedException if login was unsuccessful.
                raise LoginFailedException("Login to Intercommerce failed. Please check your credentials.")

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

    def _get_row_data(self, row_id: int, wait: WebDriverWait, save_dir: str) -> Row:
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

    def _get_release_table(self) -> None:
        pass

    def _get_container_number_from_pdf(self) -> None:
        pass

    def crawl_database(self, account: Account, dates: Dates, branch: str) -> None:

        save_dir = self._generate_save_directory(dates)

        with Driver() as (driver, wait):
            try:
                # Login to the Intercommerce system.
                driver.get(self.url)

                wait.until(EC.all_of(
                        EC.visibility_of_element_located((By.NAME, 'clientid')),
                        EC.visibility_of_element_located((By.NAME, 'password')),
                    )
                )

                driver.find_element(By.NAME, 'clientid').send_keys(account.username)
                driver.find_element(By.NAME, 'password').send_keys(account.password.get_secret_value())
                driver.find_element(By.NAME, 'form1').submit()

                # Wait for the page to load and then go to the data page.
                wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'toplink')))
                sleep(2) # ⚠️ This is a temporary fix. Our code is too fast hence. ⚠️ #

                # Offset is used to traverse the database.
                # The offset is incremented by 10 each time to get the next set of results.
                offset = 0

                # Loop through each rows of the database. The <tr> tag is used to get the rows which
                # starts from 15 to 25. The offset is used to get the next set of results.
                while True:

                    driver.get(Settings().INTERCOMMERCE_URLS[branch] + str(offset))

                    for row_id in range(15, 25):
                        try:
                            row = self._get_row_data(row_id, wait, save_dir)

                            if dates.end_date < row.creation_date < dates.start_date or row.status != 'AG':
                                raise InvalidDocumentException('The document is not valid.')

                            if dates.start_date > row.creation_date:
                                logger.info('Finished crawling the database. All rows have been cached.')
                                remove_row_from_csv('rows.csv', save_dir, row.reference_number)
                                return

                        except (InvalidDocumentException, CachedException):
                            logger.warning(f'Invalid Document. Skipping document [{Color.colorize(row.reference_number, Color.CYAN)}].')
                            continue
                    else:
                        offset += 10

            except TimeoutException:
                logger.error('Timed out. The Intercommerce database page did not load.')
                raise LoadingFailedException('Timed out. The Intercommerce database page did not load.')