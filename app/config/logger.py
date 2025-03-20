PRINT_LOG_COLORS = {
    'INFO': '\033[92m',
    'ERROR': '\033[91m',
    'WARNING': '\033[93m',
    'OTHER': '\033[96m',
    'CLEAR': '\033[0m'
}

def log_printer(log_type: str, message: str) -> None:
    """
        Prints the message with the log type.

        Parameters:
            log_type (str): the type of log message.
            message (str): the message to be printed.
    """
    print(f"{PRINT_LOG_COLORS[log_type]}{log_type}{PRINT_LOG_COLORS['CLEAR']}: {message}")