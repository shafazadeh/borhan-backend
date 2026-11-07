import re
import unicodedata
from uuid import uuid4
from contract_guard.application.use_cases.normalize_clause_numbers import normalize_clause_numbers


HEADINGS = re.compile(
    r"(?m)^\s*(?=(?:ماده\s*[\d\wآ-ی]+|تبصره(?:\s*[\d\wآ-ی]+)?|"
    r"بند\s*[\d\wآ-ی]+|(?!\d{4}[-./]\d{1,2}[-./]\d{1,2}(?:\s|$))\d+(?:\s*[-./]\s*\d+)+)\s*[:：.\-]?\s*)"
)
PREAMBLE_BOUNDARY = re.compile(r"(?<!\w)(?=مقدمات\s*[:：])")
SIMPLE_NUMBERED_CLAUSE = re.compile(r"(?m)^[ \t]*(?=\d{1,3}[.)\-–—][ \t]+[^\d\s])")
ARTICLE_HEADING = re.compile(r"^ماده\s*[\d\wآ-ی]+\s*[:：.\-–—]?[^\n]*$")
NUMBERED_CLAUSE = re.compile(r"^[ \t]*\d+(?:[ \t]*[-./][ \t]*\d+|[.)\-–—][ \t]+)")


def segment_clauses(text: str) -> list[dict]:
    normalized = unicodedata.normalize("NFC", text).translate(
        str.maketrans("يىك٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "ییک01234567890123456789")
    )
    normalized = normalized.replace("\u200b", "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]*\u200c[ \t]*", "\u200c", normalized)
    sections = HEADINGS.split(normalized)
    if sections:
        sections = PREAMBLE_BOUNDARY.split(sections[0], maxsplit=1) + sections[1:]
    expanded = []
    in_articles = False
    for section in sections:
        if re.match(r"^[ \t]*ماده\s*", section):
            in_articles = True
        expanded.extend(SIMPLE_NUMBERED_CLAUSE.split(section) if in_articles else [section])
    sections = [part for part in expanded if part.strip()]
    clauses = []
    article_title = ""
    for index, part in enumerate(sections):
        stripped = part.strip()
        first_line = stripped.split("\n", 1)[0].strip()
        is_article = bool(re.match(r"^ماده\s*", first_line))
        if is_article:
            article_title = first_line
        if (is_article and ARTICLE_HEADING.fullmatch(stripped) and index + 1 < len(sections)
                and NUMBERED_CLAUSE.match(sections[index + 1])):
            continue
        section = " ".join(part.split())
        if section:
            clauses.append({"clause_id": str(uuid4()), "index": len(clauses) + 1,
                            "text": section, "article_title": article_title})
    normalize_clause_numbers(clauses)
    return clauses
