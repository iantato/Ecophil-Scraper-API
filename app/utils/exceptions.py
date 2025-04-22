"""Custom exceptions for the Ecophil Scraper API."""

class EcophilBaseException(Exception):
    """Base class for all Ecophil exceptions."""
    pass

# Scraper Exceptions.
class ScraperException(EcophilBaseException):
    """Exception raised for errors in the scraper."""
    pass

class LoginFailedException(ScraperException):
    """Exception raised when login to the website fails."""
    pass

class LoadingFailedException(ScraperException):
    """Exception raised when loading data fails."""
    pass

class InvalidDocumentException(ScraperException):
    """Exception raised when a document is skipped."""
    pass

class ScrapedDocumentException(ScraperException):
    """Exception raised when a document is already scraped."""
    pass

class CachedException(ScraperException):
    """Exception raised when a row is already cached."""
    pass