import time
import shutil
from typing import Optional, List
from os import path, mkdir, remove

from app.config.logger import setup_logger
from app.config.config import DATA_DIR
from app.config.config import DRIVER_DOWNLOAD_TIMEOUT, DRIVER_DOWNLOAD_POLL_INTERVAL
from app.utils.colors import Color

logger = setup_logger(__name__)

def create_save_directory(directory_name: str) -> None:
    """
        Creates a directory if it does not exist.

        Parameters:
            directory_name (str): the name of the directory.
    """

    dir = path.join(DATA_DIR, 'documents', directory_name)
    cache = path.join(dir, 'cache')

    if not path.exists(dir):
        mkdir(dir)
        mkdir(cache)
        logger.info(f"Created directory: [{Color.colorize(directory_name, Color.CYAN)}] successfully.")
    else:
        logger.warning(f"Directory: [{Color.colorize(directory_name, Color.CYAN)}] already exists.")

def check_directory(directory_name: str) -> bool:
    """
        Checks if the directory exists.

        Parameters:
            directory_name (str): the name of the directory.

        Returns:
            bool: True if the directory exists, False otherwise.
    """

    dir = path.join(DATA_DIR, directory_name)
    return path.exists(dir)


def remove_directory(directory_name: str) -> None:
    """
        Removes the directory and all its contents.

        Parameters:
            directory_name (str): the name of the directory.
    """

    dir = path.join(DATA_DIR, directory_name)
    if path.exists(dir):
        remove(dir)

def wait_for_download(
    file_name: str,
    directory_name: Optional[str] = '',
    timeout: int = DRIVER_DOWNLOAD_TIMEOUT,
    poll_interval: int = DRIVER_DOWNLOAD_POLL_INTERVAL,
    temp_extensions: Optional[List[str]] = None
    ) -> bool:
    """
        Waits for the download to complete.

        Parameters:
            directory_name (str): the name of the directory.
            file_name (str): the name of the file.
            timeout (int): the timeout in seconds.
            poll_interval (int): the poll interval in seconds.
            temp_extensions (List[str]): List of temp file extensions (e.g., ['crdownload', 'tmp']).
        Returns:
            bool: True if the download is successful, False otherwise.
    """
    start_time = time.time()
    temp_extensions = temp_extensions or []
    file = path.join(DATA_DIR, directory_name, file_name)

    while time.time() - start_time < timeout:
        if not any(file_name.endswith(ext) for ext in temp_extensions) and path.exists(file):
            logger.info(f"Downloaded file: [{Color.colorize(file_name, Color.CYAN)}] successfully.")
            return True
        time.sleep(poll_interval)

    logger.error(f"Timed out. Failed to download file: [{Color.colorize(file_name, Color.CYAN)}].")
    return False