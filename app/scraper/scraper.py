from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from app.schemas.scraper import Account
from app.config.config import WEBDRIVER_WAIT_TIMEOUT

class Driver:
    def __enter__(self, wait = WEBDRIVER_WAIT_TIMEOUT['short']) -> Chrome:
        # Setup the Chrome options.
        options = ChromeOptions()

        # Enable the Chrome browser cloud management making it easier to download.
        options.add_argument('--enable-chrome-browser-cloud-management')

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

        return self.driver

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.driver.quit()
        if exc_type is not None:
            print(exc_type, exc_value, traceback)

class Scraper:

    def authenticate_vbs(self, account: Account) -> bool:
        '''
            Authenticates whether the account for VBS is valid
            or not by logging into the VBS website.

            Parameters:
                account (Account): username and password for the VBS account.

            Returns:
                bool: True if the account is valid, False otherwise.
        '''

        url = 'https://ictsi.vbs.1-stop.biz'

        with Driver() as driver:
            wait = WebDriverWait(driver, WEBDRIVER_WAIT_TIMEOUT['short'])

            try:
                driver.get(url)
                # Wait for the page to load and then login.
                wait.until(EC.all_of(
                    EC.visibility_of_element_located((By.ID, 'USERNAME')),
                    EC.visibility_of_element_located((By.ID, 'PASSWORD'))
                    )
                )

                driver.find_element(By.ID, 'USERNAME').send_keys(account.username)
                driver.find_element(By.ID, 'PASSWORD').send_keys(account.password.decode('utf-8'))
                driver.find_element(By.ID, 'form1').submit()

                # Check for login failure.
                if 'Login' in driver.page_source:
                    try:
                        wait.until(EC.visibility_of_element_located((By.ID, 'msgHolder')))
                        return False
                    except TimeoutException:
                        return True
                    except NoSuchElementException:
                        return True
                else:
                    return True

            except TimeoutException:
                print('Timed Out')
                return False