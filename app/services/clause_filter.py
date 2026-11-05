import re
import unicodedata


MIN_MEANINGFUL_CHARS = 12
RISK_TERMS = re.compile(
    r"فسخ|پرداخت|جریم[هه]|خسارت|مسئولیت|مسوولیت|متعهد|تعهد|موظف|مکلف|"
    r"الزام|ممنوع|مالکیت|محرمان|ضمانت|اختیار|هزینه|مبلغ|کارمزد|"
    r"حق(?:\s|\u200c)*الزحمه|حق(?:\s|\u200c)*فسخ|حق\s+\S+\s+(?:دارد|ندارد)|"
    r"می(?:\s|\u200c)*تواند|نمی(?:\s|\u200c)*تواند|باید|نباید|مجاز"
)
HEADING_PREFIX = re.compile(
    r"^\s*(?:(?:ماده|بند|تبصره)\s*[\w\u0600-\u06ff]+|\d+(?:\s*[-./]\s*\d+)*)\s*[:：.\-–—]*\s*"
)
IDENTITY_LABEL = re.compile(
    r"(?:نام\s*(?:و\s*نام\s*خانوادگی)?|نام\s*خانوادگی|نام\s*پدر|"
    r"شماره\s*(?:ملی|شناسنامه|تماس|همراه|تلفن|ثبت)|کد\s*(?:ملی|پستی)|"
    r"تاریخ\s*تولد|محل\s*(?:تولد|صدور)|نشانی|آدرس|تلفن|موبایل|ایمیل)"
    r"(?:\s*[:：]|(?=\s*[.…_ـ]{2,}))"
)
IDENTITY_PREFIX = re.compile(
    r"^(?:مشخصات(?:\s+(?:طرفین|طرف\s+اول|طرف\s+دوم|کارفرما|پیمانکار))?|"
    r"طرف\s+اول|طرف\s+دوم|کارفرما|پیمانکار)\s*[:：\-–—]\s*"
)
EMPTY_SUBJECT = re.compile(
    r"^(?:موضوع\s*(?:این\s*)?(?:قرارداد|توافق(?:نامه)?)(?:\s*حاضر)?[\s:：\-–—]*)?"
    r"(?:موضوع\s*(?:این\s*)?(?:قرارداد|توافق(?:نامه)?)(?:\s*حاضر)?|موضوع)"
    r"(?:\s*(?:عبارت\s*است\s*از|به\s*شرح\s*(?:زیر|ذیل)\s*است))?\s*[:：.\-…_ـ\s]*$"
)
IDENTITY_EVIDENCE = re.compile(r"شماره\s*(?:ملی|ثبت|شناسنامه|تماس)|نام\s*پدر|کد\s*ملی|نشانی|آدرس")
PLACEHOLDER = re.compile(r"[.․·…_ـ]{3,}")


def informational_reason(text: str) -> str | None:
    normalized = unicodedata.normalize("NFC", text).translate(
        str.maketrans("يىك٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "ییک01234567890123456789")
    ).replace("\u200b", "")
    normalized = " ".join(normalized.split()).strip()
    body = HEADING_PREFIX.sub("", normalized, count=1).strip()
    if RISK_TERMS.search(body):
        return None
    if body.startswith("مقدمات:") or body.startswith("مقدمات："):
        return "preamble"
    if EMPTY_SUBJECT.fullmatch(body):
        return "empty_heading"
    meaningful = sum(character.isalnum() for character in body)
    if meaningful < MIN_MEANINGFUL_CHARS:
        return "short_text"
    if len(IDENTITY_EVIDENCE.findall(body)) >= 2 and len(PLACEHOLDER.findall(body)) >= 2:
        return "identification"
    identity_body = IDENTITY_PREFIX.sub("", body, count=1)
    labels = list(IDENTITY_LABEL.finditer(identity_body))
    if labels and not identity_body[:labels[0].start()].strip(" \t،,؛;.-"):
        values = [
            identity_body[label.end():labels[index + 1].start() if index + 1 < len(labels) else len(identity_body)]
            for index, label in enumerate(labels)
        ]
        if all(len(re.findall(r"[\w\u200c]+", value)) <= 6 for value in values):
            return "identification"
    return None
