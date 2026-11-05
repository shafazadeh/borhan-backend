import re
import unicodedata
from uuid import uuid4


HEADINGS = re.compile(
    r"(?m)^\s*(?=(?:ماده\s*[\d\wآ-ی]+|تبصره(?:\s*[\d\wآ-ی]+)?|"
    r"بند\s*[\d\wآ-ی]+|\d+(?:\s*[-./]\s*\d+)+)\s*[:：.\-]?\s*)"
)
PREAMBLE_BOUNDARY = re.compile(r"(?<!\w)(?=مقدمات\s*[:：])")


def segment_clauses(text: str) -> list[dict]:
    normalized = unicodedata.normalize("NFC", text).translate(
        str.maketrans("يىك٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "ییک01234567890123456789")
    )
    normalized = normalized.replace("\u200b", "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]*\u200c[ \t]*", "\u200c", normalized)
    sections = HEADINGS.split(normalized)
    if sections:
        sections = PREAMBLE_BOUNDARY.split(sections[0], maxsplit=1) + sections[1:]
    sections = [" ".join(part.split()) for part in sections]
    return [
        {"clause_id": str(uuid4()), "index": index, "text": section}
        for index, section in enumerate((part for part in sections if part), 1)
    ]
