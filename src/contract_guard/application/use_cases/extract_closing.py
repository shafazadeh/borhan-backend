import re

SIGNATURE = re.compile(r"^[ \t]*(?:امضا(?:ی|ء)?(?:[ \t]+(?:کارفرما|پیمانکار|طرفین))?(?:[ \t]+و[ \t]+مهر)?|مهر(?:[ \t]+و[ \t]+امضا)?|اثر[ \t]+انگشت(?:[ \t]+طرفین)?)(?:[ \t]*[:：][^\n]{0,80}|[ \t.\-…_ـ]*)$", re.MULTILINE)
CLOSING = re.compile(r"(?m)^[ \t\-–—]*(?:این[ \t]+)?قرارداد(?:[ \t]+حاضر)?[ \t]+(?:در|به)[ \t]+")


def extract_closing(text: str) -> tuple[str, str]:
    # Only consider final-document material; an incidental reference to signing
    # in a legal obligation must remain in the clause.
    articles = list(re.finditer(r"(?m)^[ \t]*ماده\s*[^\s:：.\-–—]+", text))
    boundary = articles[-1].end() if articles else 0
    candidates = []
    for match in CLOSING.finditer(text, boundary):
        tail = text[match.start():match.start() + 600]
        if re.search(r"نسخه", tail) and re.search(r"تنظیم|منعقد|امضا", tail):
            candidates.append(match.start())
    signature = SIGNATURE.search(text, boundary)
    if signature:
        candidates.append(signature.start())
    if not candidates:
        return text, ""
    position = min(candidates)
    return text[:position].rstrip(), text[position:].strip()
