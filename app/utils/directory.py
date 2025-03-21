from os import path, mkdir, remove

from app.config.config import SAVES_DIR

def check_directory(directory_name) -> bool:
    """
        Checks if the directory exists.

        Parameters:
            directory_name (str): the name of the directory.

        Returns:
            bool: True if the directory exists, False otherwise.
    """

    dir = path.join(SAVES_DIR, directory_name)
    return path.exists(dir)

def create_directory(directory_name) -> None:
    """
        Creates the directory to save in for the current session.

        Parameters:
            directory_name (str): the name of the directory.
    """

    dir = path.join(SAVES_DIR, directory_name)
    mkdir(dir)
    mkdir(path.join(dir, 'sheets'))

def remove_directory(directory_name) -> None:
    """
        Removes the directory and all its contents.

        Parameters:
            directory_name (str): the name of the directory.
    """

    dir = path.join(SAVES_DIR, directory_name)
    if path.exists(dir):
        remove(dir)