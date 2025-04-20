import shutil
from os import path
from typing import Optional

from selenium.webdriver import Chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from app.utils.colors import Color
from app.scraper.driver import Driver
from app.config.logger import setup_logger
from app.config.constants import DATA_DIR, DOC_DIR
from app.models.scraper import (
    Account,
    Dates
)
from app.utils.directory import (
    wait_for_download,
    create_save_directory
)
from app.utils.exceptions import (
    LoginFailedException,
    LoadingFailedException
)

logger = setup_logger(__name__)

class VBSScraper:

    def __init__(self):
        self.url = 'https://vbs.1-stop.biz'

    def _verify_login(self, driver: Chrome, wait: WebDriverWait) -> bool:
        """
        Verify if the login was successful by checking for the presence of specific elements.
        This method checks for the presence of an error message element that indicates a failed login.

        If the error message is not found, it assumes the login was successful.

        Parameters:
            driver (Chrome): The Selenium WebDriver instance.
            wait (WebDriverWait): The WebDriverWait instance for waiting for elements.

        Returns:
            bool: True if login was successful, False otherwise.
        """
        try:
            wait.until(EC.presence_of_element_located((By.ID, 'error-element-password')))
            return False
        except TimeoutException or NoSuchElementException:
            return 'Login was unsuccessful' not in driver.page_source

    def authenticate(self, account: Account) -> bool:
        """
        Authenticate the user with the VBS system using the provided credentials.
        This method uses the Selenium WebDriver to interact with the VBS login page.
        It waits for the page to load and checks for the presence of specific elements
        to determine if the login was successful.

        Parameters:
            account (Account): The account object containing the username and password.

        Returns:
            bool: True if login was successful, False otherwise.

        Raises:
            LoginFailedException: If the login fails due to incorrect credentials.
            LoadingFailedException: If the page takes too long to load or elements are not found.
        """
        with Driver() as (driver, wait):
            try:
                driver.get(self.url)

                wait.until(EC.all_of(
                    EC.visibility_of_element_located((By.ID, 'username')),
                    EC.visibility_of_element_located((By.ID, 'password'))
                ))

                driver.find_element(By.ID, 'username').send_keys(account.username)
                driver.find_element(By.ID, 'password').send_keys(account.password.get_secret_value())
                driver.find_element(By.TAG_NAME, 'form').submit()

                login_successful = self._verify_login(driver, wait)
                if login_successful:
                    logger.info('Successfully logged in VBS account.')
                    return True

                raise LoginFailedException('Login failed. Please check your credentials.')

            except TimeoutException or NoSuchElementException:
                logger.error('Timed out. The VBS page took too long to load.')
                raise LoadingFailedException('Timed out. The VBS page took too long to load.')

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

        logger.info('Save directory initialized.')
        return save_dir

    def _accept_terms_and_conditions(self, driver: Chrome, wait: WebDriverWait, company: str) -> None:
        """
        Accept the terms and conditions for the specified company.
        This method navigates to the terms and conditions page and clicks the accept button.

        Parameters:
            driver (Chrome): The Selenium WebDriver instance.
            wait (WebDriverWait): The WebDriverWait instance for waiting for elements.
            company (str): The company name to be used in the URL.
        """
        # Go to the terms and conditions page.
        # We need to get rid of the 'https://' part of the URL to get the company
        # name hence we do the slicing [8:].
        driver.get(f'https://{company.lower()}.{self.url[8:]}/Landing.aspx?/Default.aspx?vbs_Facility_Changed=true&vbs_new_selected_FACILITYID={company.upper()}')
        wait.until(EC.element_to_be_clickable((By.ID, 'Accept'))).click()

        wait.until(EC.presence_of_element_located((By.ID, 'NotifyMessages')))
        driver.get(f'https://{company.lower()}.{self.url[8:]}/PointsTransactions.aspx')

    def _move_download_file(self, src_filename: str, dest_dir: str, dest_filename: str) -> None:
        """
        Move the downloaded file from the source directory to the save directory.

        Parameters:
            src_filename (str): The name of the source file to be moved.
            dest_dir (str): The destination directory where the file will be moved.
            dest_filename (str): The new name for the file in the destination directory.
        """
        src_path = path.join(DATA_DIR, src_filename)
        dest_path = path.join(DOC_DIR, dest_dir, dest_filename)

        shutil.move(src_path, dest_path)
        logger.info(f'File moved to [{Color.colorize(dest_path, Color.CYAN)}]')

    def download_data(self, account: Account, dates: Dates, company: str,
                      csv_filename: str, db_wait: Optional[int] = 120) -> None:
        """
        Download data from the VBS system using the provided account credentials and date range.
        This method uses the Selenium WebDriver to interact with the VBS system and download the data.

        Parameters:
            driver (Chrome): The Selenium WebDriver instance.
            wait (WebDriverWait): The WebDriverWait instance for waiting for elements.
            account (Account): The account object containing the username and password.
            dates (Dates): The Dates object containing the start and end dates.
            company (str): The company name to be used in the URL.
            csv_filename (str): The name of the CSV file to be downloaded.
        """

        save_dir = self._generate_save_directory(dates)

        with Driver() as (driver, wait):
            try:
                driver.get(self.url)

                wait.until(EC.all_of(
                        EC.visibility_of_element_located((By.ID, 'username')),
                        EC.visibility_of_element_located((By.ID, 'password'))
                    )
                )

                driver.find_element(By.ID, 'username').send_keys(account.username)
                driver.find_element(By.ID, 'password').send_keys(account.password.get_secret_value())
                driver.find_element(By.TAG_NAME, 'form').submit()

                # Wait for the page to load and then go to the terms and conditions page.
                wait.until(EC.presence_of_element_located((By.ID, 'vbs_new_selected_facilityid')))

                # Accept the terms and conditions.
                self._accept_terms_and_conditions(driver, wait, company)

                # Change the dates in the form.
                # DATE FROM.
                element = wait.until(EC.element_to_be_clickable((By.ID, 'PointsTransactionsSearchForm___DATEFROM')))
                driver.execute_script('arguments[0].removeAttribute("readonly")',
                                      element)
                element.clear()
                element.send_keys(f'{dates.start_date.day}/{dates.start_date.month}/{dates.start_date.year}')

                # DATE TO.
                element = wait.until(EC.element_to_be_clickable((By.ID, 'PointsTransactionsSearchForm___DATETO')))
                driver.execute_script('arguments[0].removeAttribute("readonly")',
                                      element)
                element.clear()
                element.send_keys(f'{dates.end_date.day}/{dates.end_date.month}/{dates.end_date.year}')

                # Request for the data from the database.
                driver.find_element(By.ID, 'PointsTransactionsSearchForm___REFERENCE').click()
                driver.find_element(By.ID, 'Search').click()

                element = WebDriverWait(driver, db_wait).until(
                    EC.element_to_be_clickable((By.ID, 'CSV'))
                )
                element.click()

                if wait_for_download('PointsTransactions.csv'):
                    self._move_download_file('PointsTransactions.csv', save_dir, csv_filename)

            except TimeoutException or NoSuchElementException:
                logger.error('Timed out. The page took too long to load.')