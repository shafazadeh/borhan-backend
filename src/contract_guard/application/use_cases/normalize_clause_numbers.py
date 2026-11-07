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


def normalize_clause_numbers(clauses: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for clause in clauses:
        groups[clause['article_title']].append(clause)
    reference_candidates = defaultdict(set)
    corrections = []
    known_articles = set()
    for title in groups:
        match = ARTICLE.match(title)
        if match:
            label = match.group(1)
            number = int(label) if label.isdecimal() else ORDINALS.get(label)
            if number is not None:
                known_articles.add(number)
    for title, group in groups.items():
        article = ARTICLE.match(title)
        if not article:
            continue
        label = article.group(1)
        expected = int(label) if label.isdecimal() else ORDINALS.get(label)
        numbered = [(item, PREFIX.match(item['text'])) for item in group]
        numbered = [(item, match) for item, match in numbered if match]
        if len(numbered) < 2:
            continue
        first, second = numbered[0][1], numbered[1][1]
        # 0-as-1 is inferred only for a 0,2 sequence with a shared article
        # number; isolated 0s and unrelated dates and amounts are untouched.
        if first.group(1) != '0' or second.group(1) != '2' or first.group(3) != second.group(3):
            continue
        raw_article = first.group(3)
        expected_text = str(expected) if expected is not None else None
        article_fix = (expected_text and raw_article != expected_text and
                       raw_article == expected_text.replace('1', '0') and '1' in expected_text)
        # Require an article-title match or the known 1-as-0 extraction pattern.
        if not expected_text or (raw_article != expected_text and not article_fix):
            continue
        if article_fix:
            reference_candidates[raw_article].add(expected_text)
        for item, match in numbered:
            if match.group(3) != raw_article:
                continue
            ordinal = '1' if item is numbered[0][0] else match.group(1)
            article_number = expected_text if article_fix else raw_article
            replacement = ordinal + '-' + article_number
            before = item['text']
            after = replacement + before[match.end():]
            if before != after:
                item.setdefault('original_text', before)
                item['text'] = after
                corrections.append({'clause_id': item['clause_id'], 'from': match.group(0), 'to': replacement})
    for raw, targets in reference_candidates.items():
        if len(targets) != 1:
            continue
        target = next(iter(targets))
        # A leading-zero reference can legitimately refer to another existing
        # article (e.g. 05 is article 5, not necessarily corrupted 15).
        if int(raw) in known_articles and int(raw) != int(target):
            continue
        expression = re.compile(r"(?<!\w)(ماده\s*)" + re.escape(raw) + r"(?!\d)")
        for item in clauses:
            before = item['text']
            after = expression.sub(lambda m: m.group(1) + target, before)
            if before != after:
                item.setdefault('original_text', before)
                item['text'] = after
                corrections.append({'clause_id': item['clause_id'], 'from': 'ماده ' + raw, 'to': 'ماده ' + target})
    return corrections
