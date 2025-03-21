class Color:
    """
    Custom color utility for adding ANSI escape codes to text.
    """

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    BOLD = "\033[1m"
    RESET = "\033[0m"

    def colorize(text: str, color: str) -> str:
        """
        Colorizes the text with the given color.

        Parameters:
            text (str): the text to be colorized.
            color (str): the color to be applied to the text.

        Returns:
            str: the colorized text.
        """
        return f"{color}{text}{Color.RESET}"