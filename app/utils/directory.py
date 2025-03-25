import time
import shutil
from typing import Optional, List
from os import path, mkdir, remove

from app.config.logger import setup_logger
from app.config.config import DATA_DIR
from app.config.config import DRIVER_DOWNLOAD_TIMEOUT, DRIVER_DOWNLOAD_POLL_INTERVAL
from app.utils.colors import Color

logger = setup_logger(__name__)

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

def create_directory(directory_name: str) -> None:
    """
        Creates the directory to save in for the current session.

        Parameters:
            directory_name (str): the name of the directory.
    """

    dir = path.join(DATA_DIR, directory_name)
    mkdir(dir)
    mkdir(path.join(dir, 'sheets'))

def remove_directory(directory_name: str) -> None:
    """
        Removes the directory and all its contents.

        Parameters:
            directory_name (str): the name of the directory.
    """

    dir = path.join(DATA_DIR, directory_name)
    if path.exists(dir):
        remove(dir)

def move_file(filename: str, from_directory: str, to_directory: str, new_filename: Optional[str] = None) -> None:
    """
        Moves the file to the appropriate directory.

        Parameters:
            filename (str): the name of the file.
            from_directory (str): the name of the directory from which to move the file.
            to_directory (str): the name of the directory to which to move the file.
            new_filename (str): the new name of the file.
    """

    if not check_directory(path.join(DATA_DIR, to_directory)):
        logger.error(f"Directory: [{Color.colorize(to_directory, Color.CYAN)}] does not exist.")
        logger.info(f"A new directory will be created: [{Color.colorize(to_directory, Color.CYAN)}].")

    from_directory = path.join(DATA_DIR, from_directory, filename)
    to_directory = path.join(DATA_DIR, to_directory, new_filename or filename)
    shutil.move(from_directory, to_directory)
    logger.info(f"Moved file: [{Color.colorize(filename, Color.CYAN)}] to directory: [{Color.colorize(to_directory, Color.CYAN)}].")

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