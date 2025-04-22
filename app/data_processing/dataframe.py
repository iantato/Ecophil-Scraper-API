from os import path
from typing import Optional

import polars as pl
from polars import Series, DataFrame

from app.config.logger import setup_logger
from app.config.constants import DOC_DIR
from app.utils.colors import Color
from app.utils.directory import check_file
from app.utils.exceptions import InvalidDocumentException

logger = setup_logger(__name__)

def load_csv_file(filename: str, save_dir: str) -> DataFrame:
    """
    Loads a CSV file from the specified directory.

    Parameters:
        filename (str): The name of the CSV file to load.
        directory (str): The directory where the CSV file is located.

    Returns:
        DataFrame: A Polars DataFrame containing the data from the CSV file.
    """
    if check_file(filename, 'documents', save_dir, 'cache'):
        return pl.read_csv(path.join(DOC_DIR, save_dir, 'cache', filename))

def get_date_from_container_number(container_number: str, filename: Optional[str], directory: Optional[str]) -> Series:
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