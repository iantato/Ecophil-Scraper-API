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