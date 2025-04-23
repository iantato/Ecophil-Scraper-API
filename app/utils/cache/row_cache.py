from os import path
from typing import List

import polars as pl
from polars import Series

from app.models.scraper import Row
from app.utils.colors import Color
from app.config.logger import setup_logger
from app.config.constants import DOC_DIR
from app.data_processing.dataframe import load_csv_file
from app.utils.directory import check_file
from app.utils.exceptions import CachedException

logger = setup_logger(__name__)

def cache_row(row: List[Row], save_dir: str) -> None:
    """
    Cache a row of data into a CSV file.

    Parameters:
        row (List[Row]): The row of data to cache.
        save_dir (str): The directory where the cached rows are stored.

    Raises:
        CachedException: If the reference number already exists in the cache.
    """
    cache_file = path.join(DOC_DIR, save_dir, 'cache', 'rows.csv')

    if not check_file('rows.csv', 'documents', save_dir, 'cache'):
        pl.DataFrame(row).write_csv(cache_file)
        logger.info(f'Row with reference number [{Color.colorize(row[0].reference_number, Color.CYAN)}] cached successfully.')
        return

    if _check_reference_number(row[0].reference_number, save_dir):
        logger.warning(f'The reference number [{Color.colorize(row[0].reference_number, Color.CYAN)}] already exists in the cache.')
        raise CachedException('The reference number already exists in the cache.')

    # Load the existing cache and append the new row.
    old_cache = load_csv_file('rows.csv', save_dir)
    old_cache = old_cache.with_columns(pl.col('creation_date').str.to_date('%Y-%m-%d')) # Convert the creation_date column to date type since
                                                                                        # CSV files cannot store date types and are stored as strings
                                                                                        # by default.
    new_cache = pl.concat([old_cache, pl.DataFrame(row)])
    new_cache.write_csv(cache_file)

    logger.info(f'Row with reference number [{Color.colorize(row[0].reference_number, Color.CYAN)}] cached successfully.')

def remove_row_from_csv(filename: str, save_dir: str, reference_number: str) -> None:
    """
    Removes a row from a CSV file based on the reference number.

    Parameters:
        filename (str): The name of the CSV file to modify.
        save_dir (str): The directory where the CSV file is located.
        reference_number (str): The reference number of the row to remove.
    """
    if check_file(filename, 'documents', save_dir, 'cache'):
        df = load_csv_file(filename, save_dir)
        df = df.remove(pl.col('reference_number') == reference_number)
        df.write_csv(path.join(DOC_DIR, save_dir, 'cache', filename))

def _check_reference_number(reference_number: str, save_dir: str) -> bool:
    """
    Check if the reference number exists in the cached rows.
    This function reads the cached CSV file and filters the rows based on the reference number.

    If the reference number is found, it returns True; otherwise, it returns False.

    Parameters:
        reference_number (str): The reference number to check.
        save_dir (str): The directory where the cached rows are stored.

    Returns:
        bool: True if the reference number exists in the cached rows, False otherwise.
    """
    cache_file = path.join(DOC_DIR, save_dir, 'cache', 'rows.csv')

    # Check if the reference number exists in the cached rows already.
    query = (
        pl.scan_csv(cache_file)
        .filter(pl.col('reference_number') == reference_number)
    )

    # Check if the query result is empty. Thus, the reference number does not exist.
    return not query.collect().is_empty()

def get_reference_numbers(filename: str, save_dir: str) -> Series:
    """
    Get the reference numbers from the cached rows.

    Parameters:
        filename (str): The name of the CSV file to read.
        save_dir (str): The directory where the CSV file is located.

    Returns:
        Series[str]: A Series containing the reference numbers.
    """
    if check_file(filename, 'documents', save_dir, 'cache'):
        df = load_csv_file(filename, save_dir)
        return df.get_column('reference_number')

def check_scraped(reference_number: str, filename: str, save_dir: str) -> bool:
    if check_file(filename, 'documents', save_dir, 'cache'):
        df = load_csv_file(filename, save_dir)
        return df.filter(pl.col('reference_number') == reference_number).select('scraped').item()