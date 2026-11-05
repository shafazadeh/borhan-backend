import io
import json
import os
import subprocess
import sys
import zipfile

from fastapi import HTTPException
from pypdf import PdfReader


PDF_TYPE = "application/pdf"
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_ZIP_ENTRIES = 2000
MAX_ZIP_TOTAL = 100 * 1024 * 1024
MAX_ZIP_RATIO = 100


def validate_document(data: bytes, declared_type: str) -> str:
    if data.startswith(b"%PDF-") and declared_type == PDF_TYPE:
        try:
            reader = PdfReader(io.BytesIO(data), strict=True)
            if reader.is_encrypted or not reader.pages:
                raise ValueError
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid or encrypted PDF") from None
        return "pdf"
    if data.startswith(b"PK\x03\x04") and declared_type == DOCX_TYPE:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries = archive.infolist()
                if len(entries) > MAX_ZIP_ENTRIES or sum(item.file_size for item in entries) > MAX_ZIP_TOTAL:
                    raise ValueError
                names = {item.filename for item in entries}
                if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                    raise ValueError
                for item in entries:
                    name = item.filename.replace("\\", "/").lower()
                    if item.flag_bits & 1 or name.startswith("/") or ".." in name.split("/"):
                        raise ValueError
                    if name.endswith(("vbaproject.bin", ".exe", ".dll")) or "/embeddings/" in name:
                        raise ValueError
                    if item.file_size > max(item.compress_size, 1) * MAX_ZIP_RATIO:
                        raise ValueError
                if archive.testzip() is not None:
                    raise ValueError
        except (ValueError, OSError, RuntimeError, zipfile.BadZipFile):
            raise HTTPException(status_code=422, detail="Invalid or unsafe DOCX") from None
        return "docx"
    raise HTTPException(status_code=415, detail="Unsupported or mismatched document type")


def extract_document(data: bytes, declared_type: str) -> str:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.services.document_worker", declared_type],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        payload = json.loads(result.stdout)
        if "error" in payload:
            raise HTTPException(status_code=payload["error"], detail="Unable to extract document")
        return payload["text"]
    except HTTPException:
        raise
    except (subprocess.SubprocessError, OSError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=422, detail="Unable to extract document") from None
