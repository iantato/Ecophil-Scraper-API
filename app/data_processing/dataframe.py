from typing import Optional
from os import path

import polars as pl
from polars import Series

from app.config.logger import setup_logger
from app.utils.colors import Color
from app.utils.exceptions import InvalidDocumentException

logger = setup_logger(__name__)

def get_date_from_container_number(container_number: str, filename: Optional[str], directory: Optional[str]) -> Series:
    '''
        Retrieves the release date of a container from a CSV file.

        Parameters:
            container_number (str): The container number to search for.
            filename (str): The name of the CSV file to read.
            directory (str): The directory where the CSV file is located.

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