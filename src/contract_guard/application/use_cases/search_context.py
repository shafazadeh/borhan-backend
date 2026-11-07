from contract_guard.domain.models.taxonomy import Category

CATEGORY_FA = {
    Category.financial: 'امور مالی و پرداخت', Category.penalty_compensation: 'خسارت و وجه التزام',
    Category.intellectual_property: 'مالکیت فکری و سورس کد', Category.confidentiality: 'محرمانگی و عدم افشا',
    Category.termination: 'فسخ و خاتمه قرارداد', Category.scope_delivery: 'شرح وظایف و تحویل',
    Category.warranty_support: 'گارانتی و پشتیبانی', Category.dispute_resolution: 'حل اختلاف و داوری',
    Category.force_majeure: 'فورس ماژور', Category.general_legal: 'شروط عمومی و اداری',
    Category.non_compete: 'عدم رقابت', Category.sla_obligations: 'تعهدات و سطح خدمات',
}


def search_context(article_title: str, category: Category, text: str) -> str:
    return f"[{article_title} | دسته‌بندی: {CATEGORY_FA[category]}] \n متن بند: {text}"
