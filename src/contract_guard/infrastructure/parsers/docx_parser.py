import io
import zipfile
from docx import Document
from docx.table import Table
from contract_guard.domain.exceptions import ContractFormatError
from contract_guard.config.settings import Settings


class DocxParser:
    def extract(self, data: bytes) -> str:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries = archive.infolist()
                if len(entries) > Settings().docx_max_entries or sum(x.file_size for x in entries) > Settings().docx_max_uncompressed_bytes:
                    raise ValueError("Oversized archive")
                for item in entries:
                    name = item.filename.replace("\\", "/").lower()
                    if (item.flag_bits & 1 or name.startswith("/") or ".." in name.split("/")
                            or name.endswith(("vbaproject.bin", ".exe", ".dll"))
                            or "/embeddings/" in name or item.file_size > max(item.compress_size, 1) * Settings().docx_max_compression_ratio):
                        raise ValueError("Unsafe archive")
            doc = Document(io.BytesIO(data))
            pieces = []
            for block in doc.iter_inner_content():
                if isinstance(block, Table):
                    pieces.extend(" | ".join(cell.text for cell in row.cells) for row in block.rows)
                else:
                    pieces.append(block.text)
            text = "\n".join(pieces).strip()
            if not text or len(text) > Settings().extraction_max_chars:
                raise ValueError("Empty or oversized text")
            return text
        except Exception as exc:
            raise ContractFormatError("Unable to extract DOCX") from exc
