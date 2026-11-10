"""Seed short statutory excerpts; embeddings remain NULL until a provider is configured."""
import asyncio
import logging
import sys
import uuid

import psycopg
from psycopg.types.json import Jsonb

from contract_guard.config.settings import Settings

logger = logging.getLogger(__name__)

# These are excerpts, not necessarily the complete articles (including notes).
ARTICLES = [
    ("قانون مدنی", "ماده ۱۰", "آزادی قراردادها", "قراردادهای خصوصی نسبت به کسانی که آن را منعقد نموده‌اند در صورتی که مخالف صریح قانون نباشد نافذ است.", "general_legal", "https://haghparvar.ir/laws/civil-code"),
    ("قانون مدنی", "ماده ۲۱۹", "لزوم قراردادها", "عقودی که بر طبق قانون واقع شده باشد بین متعاملین و قائم مقام آنها لازم‌الاتباع است مگر اینکه به رضای طرفین اقاله یا به علت قانونی فسخ شود.", "general_legal", "https://haghparvar.ir/laws/civil-code"),
    ("قانون مدنی", "ماده ۲۲۰", "آثار عقد", "عقود نه فقط متعاملین را به اجرای چیزی که در آن تصریح شده است ملزم می‌نماید بلکه متعاملین به کلیه نتایجی هم که به موجب عرف و عادت یا به موجب قانون از عقد حاصل می‌شود ملزم می‌باشند.", "general_legal", "https://haghparvar.ir/laws/civil-code"),
    ("قانون مدنی", "ماده ۲۲۶", "مطالبه خسارت", "در مورد عدم ایفای تعهدات از طرف یکی از متعاملین طرف دیگر نمی‌تواند ادعای خسارت نماید مگر اینکه برای ایفای تعهد مدت معینی مقرر شده و مدت مزبور منقضی شده باشد و اگر برای ایفای تعهد مدتی مقرر نبوده طرف وقتی می‌تواند ادعای خسارت نماید که اختیار موقع انجام با او بوده و ثابت نماید که انجام تعهد را مطالبه کرده است.", "penalty", "https://haghparvar.ir/laws/civil-code"),
    ("قانون مدنی", "ماده ۲۳۰", "وجه التزام", "اگر در ضمن معامله شرط شده باشد که در صورت تخلف، متخلف مبلغی به عنوان خسارت تأدیه نماید حاکم نمی‌تواند او را به بیشتر یا کمتر از آنچه که ملزم شده است محکوم کند.", "penalty", "https://haghparvar.ir/laws/civil-code"),
    ("قانون تجارت الکترونیکی", "ماده ۳۳", "اطلاعات پیش از قرارداد", "فروشندگان کالا و ارائه دهندگان خدمات بایستی اطلاعات مؤثر در تصمیم‌گیری مصرف‌کنندگان جهت خرید و یا قبول شرایط را از زمان مناسبی قبل از عقد در اختیار مصرف‌کنندگان قرار دهند.", "fairness", "https://dadyar.org/library/laws/electronic-commerce-law"),
    ("قانون تجارت الکترونیکی", "ماده ۴۶", "شروط غیرمنصفانه", "استفاده از شروط قراردادی خلاف مقررات این فصل و همچنین اعمال شروط غیرمنصفانه به ضرر مصرف‌کننده، مؤثر نیست.", "fairness", "https://dadyar.org/library/laws/electronic-commerce-law"),
    ("قانون کار", "ماده ۷", "تعریف قرارداد کار", "قرارداد کار عبارت است از قرارداد کتبی یا شفاهی که به موجب آن کارگر در قبال دریافت حق‌السعی کاری را برای مدت موقت یا مدت غیر موقت برای کارفرما انجام می‌دهد.", "general_legal", "https://www.irancodify.com/b/10bf598f-37d1-424d-8fec-3e88f1fc21b4"),
    ("قانون کار", "ماده ۱۰", "مندرجات قرارداد کار", "قرارداد کار علاوه بر مشخصات دقیق طرفین، باید حاوی موارد ذیل باشد: الف - نوع کار یا حرفه یا وظیفه‌ای که کارگر باید به آن اشتغال یابد. ب - حقوق یا مزد مبنا و لواحق آن. ج - ساعات کار، تعطیلات و مرخصی‌ها.", "general_legal", "https://lawlex.ir/laws/kar/10"),
]


async def make_embedding(content: str) -> None:
    """Hook for a future embedding provider; never store a fabricated vector."""
    return None


async def seed():
    inserted = 0
    async with await psycopg.AsyncConnection.connect(Settings().database_url) as connection:
        for source, number, title, content, category, url in ARTICLES:
            embedding = await make_embedding(content)
            cursor = await connection.execute(
                """INSERT INTO legal_knowledge_base
                   (id, source_name, article_number, article_title, content, category, metadata, embedding)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (source_name, article_number) DO NOTHING RETURNING id""",
                (uuid.uuid4(), source, number, title, content, category,
                 Jsonb({"source_url": url, "content_scope": "excerpt"}), embedding),
            )
            inserted += int(await cursor.fetchone() is not None)
    logger.info("Legal KB seed: %s inserted, %s already present", inserted, len(ARTICLES) - inserted)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed())
