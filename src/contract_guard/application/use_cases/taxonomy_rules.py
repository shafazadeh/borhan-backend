import re
import unicodedata
from contract_guard.domain.models.taxonomy import Category, ClauseInput, Classification, ClassificationSource

RULES = {
    Category.financial: (('مبلغ قرارداد', 'پرداخت', 'حق الزحمه', 'حق‌الزحمه', 'پیش پرداخت', 'پیش‌پرداخت', 'قسط', 'اقساط', 'تسویه', 'شماره شبا', 'مالیات', 'کسورات', 'دستمزد', 'صورت حساب', 'صورتحساب'), ('مبلغ قرارداد', 'امور مالی', 'نحوه پرداخت', 'شرایط پرداخت', 'حق الزحمه')),
    Category.penalty_compensation: (('وجه التزام', 'جبران خسارت', 'جریمه', 'خسارت', 'دیرکرد', 'تاخیر در تحویل', 'تأخیر در تحویل', 'خسارات وارد', 'خسارت تاخیر', 'خسارت تأخیر', 'ضرر و زیان'), ('وجه التزام', 'خسارت', 'جرایم', 'جریمه')),
    Category.intellectual_property: (('مالکیت فکری', 'مالکیت معنوی', 'مالکیت کد', 'مالکیت سورس', 'حق نشر', 'حق تالیف', 'حق تألیف', 'سورس کد', 'سورس‌کد', 'لایسنس', 'مجوز بهره برداری', 'ریپازیتوری', 'گیت'), ('مالکیت فکری', 'مالکیت معنوی', 'حقوق مالکیت', 'سورس کد')),
    Category.confidentiality: (('محرمانگی', 'محرمانه', 'اسرار تجاری', 'عدم افشا', 'عدم افشاء', 'عدم‌افشا', 'افشای اطلاعات', 'افشا', 'اطلاعات حساس', 'حفظ اسرار'), ('محرمانگی', 'عدم افشا', 'عدم افشاء', 'اطلاعات محرمانه')),
    Category.termination: (('فسخ', 'خاتمه قرارداد', 'پایان قرارداد', 'انفساخ', 'حق فسخ', 'انصراف', 'اختیار خاتمه'), ('فسخ قرارداد', 'خاتمه قرارداد', 'فسخ', 'انفساخ')),
    Category.scope_delivery: (('موضوع قرارداد', 'شرح خدمات', 'شرح وظایف', 'تحویل', 'پذیرش', 'فازبندی', 'فاز', 'تست پذیرش', 'مراحل اجرا', 'طراحی', 'برنامه نویسی', 'برنامه‌نویسی'), ('موضوع قرارداد', 'شرح خدمات', 'شرح وظایف', 'تحویل', 'دامنه کار')),
    Category.warranty_support: (('گارانتی', 'پشتیبانی', 'رفع باگ', 'رفع ایراد', 'رفع اشکال', 'ضمانت خدمات', 'دوره پشتیبانی', 'عیب یابی', 'عیب‌یابی', 'رفع نواقص'), ('گارانتی', 'پشتیبانی', 'ضمانت خدمات')),
    Category.dispute_resolution: (('حل اختلاف', 'داوری', 'داور', 'مرجع رسیدگی', 'دادگاه', 'مراجع قضایی', 'شورای حل اختلاف', 'مرجع صالح'), ('حل اختلاف', 'داوری', 'مرجع رسیدگی')),
    Category.force_majeure: (('فورس ماژور', 'فورس‌ماژور', 'قوه قاهره', 'حوادث قهری', 'بلایای طبیعی', 'قطعی سراسری اینترنت', 'شرایط اضطراری', 'قوای قهری'), ('فورس ماژور', 'فورس‌ماژور', 'قوه قاهره')),
    Category.non_compete: (('عدم رقابت', 'رقابت', 'فعالیت مشابه', 'عدم همکاری با رقبا', 'ممنوعیت فعالیت'), ('عدم رقابت', 'منع رقابت')),
    Category.sla_obligations: (('رفع نقص', 'پشتیبانی', 'تعهدات پیمانکار', 'ساعت کاری', 'حضور در محل', 'مدت زمان پاسخگویی', 'زمان پاسخگویی'), ('تعهدات پیمانکار', 'سطح خدمات')),
    Category.general_legal: (('مشخصات طرفین', 'اقامتگاه قانونی', 'نشانی', 'ابلاغ', 'مکاتبات', 'نسخ قرارداد', 'نسخه قرارداد', 'قانون حاکم', 'تفکیک پذیری', 'تفکیک‌پذیری'), ('مشخصات طرفین', 'اقامتگاه', 'ابلاغ', 'مکاتبات', 'قانون حاکم', 'تفکیک پذیری')),
}


def normalize(value):
    value = unicodedata.normalize('NFKC', value).translate(str.maketrans('يىك', 'ییک')).replace('‌', ' ')
    return re.sub(r'\s+', ' ', value).strip()


PREPARED_RULES = {
    category: (
        [(normalize(word), word) for word in sorted(words, key=len, reverse=True)],
        [(normalize(word), word) for word in titles],
    )
    for category, (words, titles) in RULES.items()
}


EXPLICIT_CATEGORIES = {Category.non_compete, Category.penalty_compensation, Category.confidentiality, Category.sla_obligations}


def classify_rule(clause: ClauseInput) -> Classification | None:
    body, title = normalize(clause.text), normalize(clause.article_title)
    hits = []
    for category, (words, titles) in PREPARED_RULES.items():
        keywords = []
        normalized_hits = []
        for normalized, word in words:
            if normalized in body and not any(normalized in existing for existing in normalized_hits):
                keywords.append(word)
                normalized_hits.append(normalized)
        title_hits = [word for normalized, word in titles if normalized in title]
        if len(keywords) >= 2 or title_hits or (category in EXPLICIT_CATEGORIES and keywords):
            hits.append((category, keywords, title_hits))
    if not hits:
        return None
    if len(hits) > 1:
        explicit = [hit for hit in hits if hit[0] in EXPLICIT_CATEGORIES and hit[1]]
        if not explicit:
            return None
        # Longer, more specific evidence wins. Other matched categories remain visible.
        hits.sort(key=lambda hit: (hit in explicit, max((len(normalize(k)) for k in hit[1]), default=0),
                                   len(hit[1]), bool(hit[2])), reverse=True)
    category, keywords, title_hits = hits[0]
    all_keywords = list(dict.fromkeys(word for _, words, titles in hits for word in words + titles))
    return Classification(clause_id=clause.clause_id, primary_category=category,
        secondary_categories=[hit[0] for hit in hits[1:]], confidence=0.9,
        matched_keywords=all_keywords, source=ClassificationSource.rule_based)
