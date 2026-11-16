#readers.py 

import csv
import importlib
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=None)
def get_module(name):
    return importlib.import_module(name)


@lru_cache(maxsize=1)
def get_ocr_engine():
    PaddleOCR = get_module("paddleocr").PaddleOCR

    return PaddleOCR(
        lang="en",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False
    )


def make_result(path, blocks, method, metadata=None):
    return {
        "filename": Path(path).name,
        "file_type": Path(path).suffix.lower().lstrip(".") or "unknown",
        "status": "success",
        "content": to_markdown(blocks),
        "extraction_method": method,
        "metadata": metadata or {}
    }


def to_markdown(blocks):
    output = []

    for block in blocks:
        block_type = block["type"]
        value = block["content"]

        if block_type == "heading":
            level = block.get("level", 1)
            output.append(f"{'#' * level} {value}")

        elif block_type == "text":
            if value.strip():
                output.append(value.strip())

        elif block_type == "table":
            table = table_to_markdown(value)

            if table:
                output.append(table)

    return "\n\n".join(output)


def table_to_markdown(rows):
    if not rows:
        return ""

    rows = [
        [clean_cell(value) for value in row]
        for row in rows
    ]

    width = max(len(row) for row in rows)

    rows = [
        row + [""] * (width - len(row))
        for row in rows
    ]

    rows = [
        row for row in rows
        if any(cell for cell in row)
    ]

    if not rows:
        return ""

    output = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join(["---"] * width) + " |"
    ]

    for row in rows[1:]:
        output.append("| " + " | ".join(row) + " |")

    return "\n".join(output)


def clean_cell(value):
    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .replace("|", "\\|")
        .replace("\r\n", "<br>")
        .replace("\n", "<br>")
    )


def run_ocr(image):
    ocr = get_ocr_engine()
    results = ocr.predict(image)

    text_parts = []
    confidences = []

    for result in results:
        for text, score in zip(
            result["rec_texts"],
            result["rec_scores"]
        ):
            if str(text).strip():
                text_parts.append(str(text).strip())
                confidences.append(float(score))

    confidence = (
        sum(confidences) / len(confidences)
        if confidences else None
    )

    return "\n".join(text_parts), confidence


def read_pdf(path):
    pymupdf = get_module("pymupdf")
    pdfplumber = get_module("pdfplumber")
    np = get_module("numpy")
    Image = get_module("PIL.Image")

    path = Path(path)
    blocks = []
    ocr_pages = []
    table_count = 0

    with pymupdf.open(path) as pdf:
        page_count = pdf.page_count

        with pdfplumber.open(path) as table_pdf:
            for index, page in enumerate(pdf):
                page_number = index + 1

                blocks.append({
                    "type": "heading",
                    "content": f"Page {page_number}",
                    "level": 1
                })

                text = page.get_text("text", sort=True).strip()

                if text:
                    blocks.append({
                        "type": "text",
                        "content": text
                    })

                else:
                    pixmap = page.get_pixmap(
                        matrix=pymupdf.Matrix(2, 2),
                        alpha=False
                    )

                    image = Image.frombytes(
                        "RGB",
                        (pixmap.width, pixmap.height),
                        pixmap.samples
                    )

                    image_array = np.array(image)
                    image_array = image_array[:, :, ::-1].copy()

                    ocr_text, confidence = run_ocr(image_array)

                    blocks.append({
                        "type": "heading",
                        "content": "OCR Extracted Text",
                        "level": 2
                    })

                    blocks.append({
                        "type": "text",
                        "content": ocr_text
                    })

                    ocr_pages.append(page_number)

                tables = table_pdf.pages[index].extract_tables()

                for table in tables:
                    if table:
                        table_count += 1

                        blocks.append({
                            "type": "heading",
                            "content": f"Table {table_count}",
                            "level": 2
                        })

                        blocks.append({
                            "type": "table",
                            "content": table
                        })

    methods = ["pymupdf", "pdfplumber"]

    if ocr_pages:
        methods.append("paddleocr")

    return make_result(
        path,
        blocks,
        methods,
        metadata={
            "page_count": page_count,
            "ocr_pages": ocr_pages,
            "table_count": table_count
        }
    )


def read_spreadsheet(path):
    load_workbook = get_module("openpyxl").load_workbook

    path = Path(path)
    blocks = []
    sheet_names = []

    workbook = load_workbook(
        path,
        read_only=True,
        data_only=False
    )

    for sheet in workbook.worksheets:
        sheet_names.append(sheet.title)

        blocks.append({
            "type": "heading",
            "content": sheet.title,
            "level": 1
        })

        rows = list(
            sheet.iter_rows(values_only=True)
        )

        blocks.append({
            "type": "table",
            "content": rows
        })

    workbook.close()

    return make_result(
        path,
        blocks,
        ["openpyxl"],
        metadata={
            "sheet_count": len(sheet_names),
            "sheets": sheet_names
        }
    )


def read_csv(path):
    path = Path(path)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        sample = file.read(8192)
        file.seek(0)

        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel

        rows = list(csv.reader(file, dialect))

    blocks = [
        {
            "type": "heading",
            "content": path.name,
            "level": 1
        },
        {
            "type": "table",
            "content": rows
        }
    ]

    return make_result(
        path,
        blocks,
        ["python-csv"],
        metadata={
            "row_count": len(rows)
        }
    )


def read_word(path):
    Document = get_module("docx").Document
    Paragraph = get_module("docx.text.paragraph").Paragraph
    Table = get_module("docx.table").Table

    path = Path(path)
    document = Document(path)
    blocks = []

    for element in document.iter_inner_content():

        if isinstance(element, Paragraph):
            if element.text.strip():
                blocks.append({
                    "type": "text",
                    "content": element.text
                })

        elif isinstance(element, Table):
            rows = [
                [cell.text for cell in row.cells]
                for row in element.rows
            ]

            blocks.append({
                "type": "table",
                "content": rows
            })

    for index, section in enumerate(document.sections, start=1):
        header = [
            paragraph.text
            for paragraph in section.header.paragraphs
            if paragraph.text.strip()
        ]

        footer = [
            paragraph.text
            for paragraph in section.footer.paragraphs
            if paragraph.text.strip()
        ]

        if header:
            blocks.append({
                "type": "heading",
                "content": f"Header - Section {index}",
                "level": 2
            })

            blocks.append({
                "type": "text",
                "content": "\n".join(header)
            })

        if footer:
            blocks.append({
                "type": "heading",
                "content": f"Footer - Section {index}",
                "level": 2
            })

            blocks.append({
                "type": "text",
                "content": "\n".join(footer)
            })

    return make_result(
        path,
        blocks,
        ["python-docx"],
        metadata={
            "paragraph_count": len(document.paragraphs),
            "table_count": len(document.tables),
            "section_count": len(document.sections)
        }
    )


def read_image(path):
    np = get_module("numpy")
    Image = get_module("PIL.Image")
    ImageOps = get_module("PIL.ImageOps")

    path = Path(path)

    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
        width, height = image.size

        image_array = np.array(image)
        image_array = image_array[:, :, ::-1].copy()

        text, confidence = run_ocr(image_array)

    blocks = [
        {
            "type": "text",
            "content": text
        }
    ]

    return make_result(
        path,
        blocks,
        ["paddleocr"],
        metadata={
            "image_width": width,
            "image_height": height,
            "ocr_confidence": confidence
        }
    )


def read_html(path):
    BeautifulSoup = get_module("bs4").BeautifulSoup

    path = Path(path)
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    blocks = []

    for element in soup.find_all(
        ["h1", "h2", "h3", "p", "li", "table"]
    ):
        if element.name in ["h1", "h2", "h3"]:
            blocks.append({
                "type": "heading",
                "content": element.get_text(" ", strip=True),
                "level": int(element.name[1])
            })

        elif element.name == "table":
            rows = []

            for row in element.find_all("tr"):
                cells = row.find_all(
                    ["th", "td"],
                    recursive=False
                )

                if cells:
                    rows.append([
                        cell.get_text(" ", strip=True)
                        for cell in cells
                    ])

            blocks.append({
                "type": "table",
                "content": rows
            })

        else:
            blocks.append({
                "type": "text",
                "content": element.get_text(" ", strip=True)
            })

    return make_result(
        path,
        blocks,
        ["beautifulsoup4"]
    )


def read_text(path):
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")

    blocks = [
        {
            "type": "heading",
            "content": path.name,
            "level": 1
        },
        {
            "type": "text",
            "content": text
        }
    ]

    return make_result(
        path,
        blocks,
        ["python-text"]
    )


def read_document(path):
    path = Path(path)

    readers = {
        ".pdf": read_pdf,
        ".xlsx": read_spreadsheet,
        ".csv": read_csv,
        ".docx": read_word,
        ".jpg": read_image,
        ".jpeg": read_image,
        ".png": read_image,
        ".tif": read_image,
        ".tiff": read_image,
        ".bmp": read_image,
        ".html": read_html,
        ".htm": read_html,
        ".txt": read_text,
        ".md": read_text
    }

    reader = readers.get(path.suffix.lower())

    if reader is None:
        return {
            "filename": path.name,
            "file_type": path.suffix.lower().lstrip(".") or "unknown",
            "status": "unsupported",
            "content": "",
            "extraction_method": [],
            "metadata": {}
        }

    return reader(path)
