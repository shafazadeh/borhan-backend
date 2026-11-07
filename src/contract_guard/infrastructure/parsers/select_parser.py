from contract_guard.infrastructure.parsers.docx_parser import DocxParser
from contract_guard.infrastructure.parsers.pdf_parser import PdfParser


def select_parser(kind: str, data: bytes):
    """Choose a parser only when the declared type matches the file signature."""
    if kind == "pdf" and data.startswith(b"%PDF-"):
        return PdfParser()
    if kind == "docx" and data.startswith(b"PK\x03\x04"):
        return DocxParser()
    raise ValueError("Invalid file")
