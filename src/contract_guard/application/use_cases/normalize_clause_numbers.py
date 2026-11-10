import re
from collections import defaultdict

ORDINALS = {
    "اول": 1, "یک": 1, "یکم": 1, "دوم": 2, "سوم": 3, "چهارم": 4,
    "پنجم": 5, "ششم": 6, "هفتم": 7, "هشتم": 8, "نهم": 9, "دهم": 10,
    "یازدهم": 11, "دوازدهم": 12, "سیزدهم": 13, "چهاردهم": 14,
    "پانزدهم": 15, "شانزدهم": 16, "هفدهم": 17, "هجدهم": 18,
    "نوزدهم": 19, "بیستم": 20,
}
PREFIX = re.compile(r"^(\d{1,3})(\s*[-./]\s*)(\d{1,3})(?=\s|[.):]|$)")
ARTICLE = re.compile(r"^ماده\s*([^\s:：.\-–—]+)")


def _article_number(title: str) -> int | None:
    match = ARTICLE.match(title)
    if not match:
        return None
    label = match.group(1)
    return int(label) if label.isdecimal() else ORDINALS.get(label)


def _record_correction(item: dict, after: str, old: str, new: str, corrections: list[dict]) -> None:
    before = item["text"]
    if before != after:
        item.setdefault("original_text", before)
        item["text"] = after
        corrections.append({"clause_id": item["clause_id"], "from": old, "to": new})


def _correct_group(title: str, group: list[dict], candidates: dict, corrections: list[dict]) -> None:
    if not ARTICLE.match(title):
        return
    expected = _article_number(title)
    numbered = [(item, match) for item in group if (match := PREFIX.match(item["text"]))]
    if len(numbered) < 2:
        return
    first, second = numbered[0][1], numbered[1][1]
    # Infer a misread zero only from a 0,2 sequence in the same article.
    if first.group(1) != "0" or second.group(1) != "2" or first.group(3) != second.group(3):
        return
    raw = first.group(3)
    expected_text = str(expected) if expected is not None else None
    article_fix = (expected_text and raw != expected_text and
                   raw == expected_text.replace("1", "0") and "1" in expected_text)
    if not expected_text or (raw != expected_text and not article_fix):
        return
    if article_fix:
        candidates[raw].add(expected_text)
    for item, match in numbered:
        if match.group(3) != raw:
            continue
        ordinal = "1" if item is numbered[0][0] else match.group(1)
        replacement = ordinal + "-" + (expected_text if article_fix else raw)
        _record_correction(item, replacement + item["text"][match.end():],
                           match.group(0), replacement, corrections)


def _correct_references(clauses: list[dict], candidates: dict, known_articles: set[int],
                        corrections: list[dict]) -> None:
    for raw, targets in candidates.items():
        if len(targets) != 1:
            continue
        target = next(iter(targets))
        # A leading-zero reference may refer to a different existing article.
        if int(raw) in known_articles and int(raw) != int(target):
            continue
        expression = re.compile(r"(?<!\w)(ماده\s*)" + re.escape(raw) + r"(?!\d)")
        for item in clauses:
            after = expression.sub(lambda match: match.group(1) + target, item["text"])
            _record_correction(item, after, "ماده " + raw, "ماده " + target, corrections)


def normalize_clause_numbers(clauses: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for clause in clauses:
        groups[clause["article_title"]].append(clause)
    known_articles = {number for title in groups if (number := _article_number(title)) is not None}
    candidates = defaultdict(set)
    corrections = []
    for title, group in groups.items():
        _correct_group(title, group, candidates, corrections)
    _correct_references(clauses, candidates, known_articles, corrections)
    return corrections
