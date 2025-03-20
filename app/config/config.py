from pathlib import Path

WEBDRIVER_WAIT_TIMEOUT: dict = {
    'short': 5,
    'medium': 30,
    'long': 60
}

# Maximum number of login attempts before closing the browser.
MAX_LOGIN_ATTEMPTS: int = 3

# Timeout in milliseconds after max attempts are reached.
LOGIN_ATTEMPT_TIMEOUT: int = 500


# The base directory of the project.
BASE_DIR = str(Path().resolve())

# The directory where we store the data.
SAVES_DIR = BASE_DIR + '/data/saves'