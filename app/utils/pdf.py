from os import remove

from PyPDF2 import PdfReader

from app.config.constants import DATA_DIR

def extract_container_number(filename: str) -> str:
    """
        Extracts the container number from a PDF file.

        Parameters:
            filename (str): The name of the PDF file.

        Returns:
            str: The extracted container number.
    """
    with open(f'{DATA_DIR}/{filename}', 'rb') as file:
        reader = PdfReader(file, strict=False)
        texts = reader.pages[0].extract_text().replace('- Container No(s) -', '').split('\n')

        for text in texts:
            if 'Container No' in text:
                container_number = text.rsplit(' ', 1)[1].strip()
                return container_number

def destroy_pdf(filename: str) -> None:
    """
        Deletes the PDF file from the server.

        Parameters:
            filename (str): The name of the PDF file.
            reference_number (str): The reference number associated with the PDF file.
    """
    remove(f'{DATA_DIR}/{filename}')