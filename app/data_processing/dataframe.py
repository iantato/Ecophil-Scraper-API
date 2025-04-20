from os import path
from typing import Optional, List

import polars as pl
from polars import Series, DataFrame

from app.config.logger import setup_logger
from app.utils.colors import Color
from app.utils.exceptions import InvalidDocumentException
from app.models.scraper import Row
from app.utils.directory import (
    check_file
)

logger = setup_logger(__name__)

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

def cache_row(row: List[Row], save_dir: str) -> None:
    """
    Caches a row of data into a CSV file using Polars.

    Parameters:
        row (List[Row]): The row of data to be cached.
        save_dir (str): The directory where the CSV file will be saved.
    """
    # Uses Polars + Pydantics to create a dataframe from the model.
    cache = pl.DataFrame(row)
    dest_dir = path.join(save_dir, 'cache')

    if not cache.is_empty() and check_file('rows_cache.csv', 'dest_dir'):
        cache.write_csv(path.join(dest_dir, 'rows_cache.csv'), mode='append')
    elif not cache.is_empty():
        cache.write_csv(path.join(dest_dir, 'rows_cache.csv'))

    # Clear the cache DataFrame after writing to the CSV file.
    cache = pl.DataFrame()
    logger.info(f"Cached row at {Color.colorize(path.join(dest_dir, 'rows_cache.csv'), Color.CYAN)}")