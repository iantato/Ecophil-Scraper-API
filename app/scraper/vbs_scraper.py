from selenium.webdriver import Chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from app.scraper.driver import Driver
from app.config.logger import setup_logger
from app.models.scraper import (
    Account
)
from app.utils.exceptions import (
    LoginFailedException,
    LoadingFailedException
)

logger = setup_logger(__name__)

class VBSScraper:

    @staticmethod
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

        url = 'https://ictsi.vbs.1-stop.biz'

        with Driver() as (driver, wait):
            try:
                driver.get(url)

                wait.until(EC.all_of(
                    EC.visibility_of_element_located((By.ID, 'username')),
                    EC.visibility_of_element_located((By.ID, 'password'))
                ))

                driver.find_element(By.ID, 'username').send_keys(account.username)
                driver.find_element(By.ID, 'password').send_keys(account.password.get_secret_value())
                driver.find_element(By.TAG_NAME, 'form').submit()

                login_successful = self.verify_login(driver, wait)
                if login_successful:
                    logger.info('Successfully logged in VBS account.')
                    return True

                raise LoginFailedException('Login failed. Please check your credentials.')

            except TimeoutException or NoSuchElementException:
                logger.error('Timed out. The VBS page took too long to load.')
                raise LoadingFailedException('Timed out. The VBS page took too long to load.')

    @staticmethod
    def _verify_login(driver: Chrome, wait: WebDriverWait) -> bool:
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

    def _accept_terms_and_conditions(self, driver: Chrome, wait: WebDriverWait, company: str) -> None:

        # Go to the terms and conditions page.
        # We need to get rid of the 'https://' part of the URL to get the company
        # name hence we do the slicing [8:].
        driver.get(f'https://{company.lower()}{self.url[8:]}/Default.aspx?vbs_Facility_Changed=true&vbs_new_selected_FACILITYID={company.upper()}')
        wait.until(EC.element_to_be_clickable((By.ID, 'Accept'))).click()

        wait.until(EC.presence_of_element_located((By.ID, 'NotifyMessages')))
        driver.get(f'https://{company.lower()}{self.url[8:]}/PointsTransactions.aspx')

    def _move_download_file(self, src_filename: str, dest_dir: str, dest_filename: str) -> None:
        pass

    def download_data(self, driver: Chrome, wait: WebDriverWait, account: Account, dates: Dates,
                      company: str, csv_filename: str, save_dir: str) -> None:

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

                if wait_for_download('PointsTransactions.csv'):
                    pass

            except TimeoutException or NoSuchElementException:
                logger.error('Timed out. The page took too long to load.')