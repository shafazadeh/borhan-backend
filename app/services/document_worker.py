import io
import json
import logging
import sys

from docx import Document
from docx.table import Table
from fastapi import HTTPException
from pypdf import PdfReader

from app.services.documents import validate_document


MAX_TEXT = 5_000_000
MAX_PAGES = 500


def docx_text(document):
    for block in document.iter_inner_content():
        if isinstance(block, Table):
            for row in block.rows:
                yield " | ".join(cell.text for cell in row.cells)
        else:
            yield block.text


def main():
    logging.disable(logging.CRITICAL)
    declared_type = sys.argv[1]
    data = sys.stdin.buffer.read(15 * 1024 * 1024 + 1)
    try:
        if len(data) > 15 * 1024 * 1024:
            raise ValueError
        kind = validate_document(data, declared_type)
        if kind == "pdf":
            reader = PdfReader(io.BytesIO(data), strict=True)
            if len(reader.pages) > MAX_PAGES:
                raise ValueError
            pieces = (page.extract_text() or "" for page in reader.pages)
        else:
            document = Document(io.BytesIO(data))
            pieces = docx_text(document)
        result = []
        size = 0
        for piece in pieces:
            size += len(piece)
            if size > MAX_TEXT:
                raise ValueError
            result.append(piece)
        text = "\n".join(result).strip()
        if not text:
            raise ValueError
        print(json.dumps({"text": text}, ensure_ascii=True))
    except HTTPException as exc:
        print(json.dumps({"error": exc.status_code}))
    except Exception:
        print(json.dumps({"error": 422}))


if __name__ == "__main__":
    main()
