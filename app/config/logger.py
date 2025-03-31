import logging
from app.utils.colors import Color

class ConsoleFormatter(logging.Formatter):
    """
    Custom formatter to add colors to the log levels in the console.
    """

    def format(self, record: logging.LogRecord) -> logging.Formatter:
        # Map log levels to colors.
        level_colors = {
            logging.DEBUG: Color.CYAN,
            logging.INFO: Color.GREEN,
            logging.WARNING: Color.YELLOW,
            logging.ERROR: Color.RED,
            logging.CRITICAL: Color.RED
        }

        record.levelname = Color.colorize(record.levelname, level_colors[record.levelno])
        return super().format(record)

def setup_logger(name: str) -> logging.Logger:
    """
    Set up and return a logger with colored console output.
    """

    # Initialize the logger.
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Create a console handler with the custom formatter.
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ConsoleFormatter(
        "%(levelname)s:     %(message)s"
    ))
    logger.addHandler(console_handler)

    return logger