from typing import Optional
from os import path

import polars as pl
from app.config.logger import setup_logger

logger = setup_logger(__name__)

def get_date_from_container_number(container_number: str, filename: Optional[str], directory: Optional[str]) -> None:
    q = (
        pl.scan_csv(path.join(directory, filename))
        .with_columns(pl.col('Event Date').str.to_datetime('%d-%b-%y %H:%M'))
        .filter((pl.col('Container') == container_number) & (pl.col('Point Event') == 'ARRIVE'))
        .collect()
    )

    return q.get_column('Event Date')