from pathlib import Path

from readers.pdf_reader import read_pdf
from readers.spreadsheet_reader import read_spreadsheet
from readers.csv_reader import read_csv
from readers.word_reader import read_word
from readers.image_reader import read_image
from readers.html_reader import read_html
from readers.text_reader import read_text


def read_document(path):
    path = Path(path)
    extension = path.suffix.lower()

    if extension == ".pdf":
        return read_pdf(path)

    elif extension in [".xlsx", ".xls"]:
        return read_spreadsheet(path)

    elif extension == ".csv":
        return read_csv(path)

    elif extension == ".docx":
        return read_word(path)

    elif extension in [".jpg", ".jpeg", ".png", ".tiff", ".tif"]:
        return read_image(path)

    elif extension in [".html", ".htm"]:
        return read_html(path)

    elif extension in [".txt", ".md"]:
        return read_text(path)

    else:
        return {
            "filename": path.name,
            "file_type": extension or "unknown",
            "status": "unsupported",
            "content": "",
            "extraction_method": [],
            "metadata": {}
        }