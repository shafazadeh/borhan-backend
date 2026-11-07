import io
from pypdf import PdfReader
from contract_guard.domain.exceptions import ContractFormatError
from contract_guard.config.settings import Settings


class PdfParser:
    def extract(self, data: bytes) -> str:
        try:
            reader = PdfReader(io.BytesIO(data), strict=True)
            if reader.is_encrypted or not reader.pages or len(reader.pages) > Settings().extraction_max_pages:
                raise ValueError("Invalid PDF")
            text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
            if not text or len(text) > Settings().extraction_max_chars:
                raise ValueError("Empty or oversized text")
            return text
        except Exception as exc:
            raise ContractFormatError("Unable to extract PDF") from exc
