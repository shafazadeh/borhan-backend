# Contract Guard

بک‌اند FastAPI برای دریافت و آماده‌سازی قراردادهای فارسی. نسخهٔ فعلی ورود با شمارهٔ موبایل، استخراج متن از PDF/DOCX، تفکیک و دسته‌بندی بندها، چانک‌سازی، تولید embedding محلی و جست‌وجوی معنایی میان چانک‌های همان کاربر را فراهم می‌کند.

> این پروژه ابزار کمکی پردازش متن است و جایگزین مشاوره یا نظر حقوقی نیست.

## وضعیت قابلیت‌ها

| قابلیت | وضعیت | توضیح |
|---|---|---|
| ورود با شمارهٔ موبایل | پیاده‌سازی‌شده | OTP توسعه، نشست و access/refresh token تصادفی (نه JWT) |
| پروفایل کاربر | پیاده‌سازی‌شده | مشاهده و ویرایش محدود `email` و `username` |
| استخراج قرارداد | پیاده‌سازی‌شده | PDF متنی و DOCX؛ ورودی و پردازش با محدودیت اندازه و زمان |
| پردازش بندها | پیاده‌سازی‌شده | نرمال‌سازی، تفکیک، تشخیص تقریبی بخش پایانی/امضا و دسته‌بندی |
| چانک‌سازی | پیاده‌سازی‌شده | قطعه‌های حداکثر ۸۰۰ کاراکتر با ۱۵۰ کاراکتر هم‌پوشانی و حفظ metadata |
| embedding و جست‌وجوی معنایی | پیاده‌سازی‌شده | مدل محلی چندزبانه با بردار ۳۸۴بعدی و `pgvector`؛ نتایج فقط به مالک داده محدود می‌شوند |
| دسته‌بندی با مدل زبانی | اختیاری | در صورت پیکربندی gateway سازگار با Chat Completions؛ در غیر این صورت مسیر قانون‌محور/حالت تنزل‌یافته استفاده می‌شود |
| پایگاه دانش حقوقی | اولیه | جدول و اسکریپت seed برای گزیده‌ای از قوانین وجود دارد، اما embedding آن‌ها، retrieval و RAG هنوز متصل نشده‌اند |
| تحلیل ریسک و گزارش نهایی | پیاده‌سازی‌نشده | فایل‌ها و قراردادهای اولیه وجود دارند، ولی endpoint و جریان عملیاتی ندارند |
| ارسال واقعی پیامک | پیاده‌سازی‌نشده | در production درخواست و تأیید ورود با 503 متوقف می‌شود |

## پیش‌نیازها

- Python 3.11 یا بالاتر
- PostgreSQL دارای افزونهٔ `pgvector` و Redis؛ ساده‌ترین راه، Docker Compose موجود در مخزن است.
- اتصال اینترنت در نخستین اجرای embedding، تا مدل `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` با revision پین‌شده دریافت شود.

## راه‌اندازی در ویندوز

در ریشهٔ پروژه:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -m pip install --upgrade pip
python -m pip install -e .
docker compose up -d postgres redis
python -m contract_guard.infrastructure.database.migrate
python -m contract_guard
```

سرور مطابق `.env` نمونه در `http://127.0.0.1:8001` اجرا می‌شود و مستندات تعاملی آن در `/docs` است. نقطهٔ ورود درست `python -m contract_guard` است؛ دستور قدیمی `uvicorn app.main:app` به این ساختار مربوط نیست.

قبل از اجرای migration روی پایگاه دادهٔ موجود، از آن نسخهٔ پشتیبان بگیرید. migration شمارهٔ ۵ اگر embeddingهای قدیمی با بعدی غیر از ۳۸۴ وجود داشته باشند، عمداً با خطا متوقف می‌شود تا داده‌ها بدون بازتولید بردارها تغییر نکنند.

### تنظیمات

تمام تنظیمات با Pydantic Settings از محیط یا `.env` خوانده می‌شوند. `.env.example` فقط مقادیر توسعه دارد و نباید با اسرار واقعی commit شود.

| گروه | متغیرهای اصلی | کاربرد |
|---|---|---|
| اجرا | `ENVIRONMENT`, `HOST`, `PORT` | محیط و نشانی سرویس |
| PostgreSQL | `DATABASE_URL`, `POSTGRES_*` | اتصال برنامه و سرویس Compose |
| Redis | `REDIS_URL`, `REDIS_*` | چالش‌های ورود، تلاش‌ها و cooldown |
| نشست و OTP | `SESSION_HOURS`, `ACCESS_TOKEN_MINUTES`, `OTP_*`, `DEV_OTP_CODE` | عمر نشست و کنترل ورود |
| استخراج | `UPLOAD_MAX_BYTES`, `EXTRACTION_*`, `DOCX_MAX_*` | سقف حجم، زمان، صفحات و ایمنی DOCX |
| embedding | `EMBEDDING_MODEL_NAME`, `EMBEDDING_MODEL_REVISION` | نام و revision مدل محلی؛ خروجی فعلی باید ۳۸۴بعدی باشد |
| LLM دسته‌بندی | `TAXONOMY_LLM_*` | gateway اختیاری برای بندهای مبهم |

`DEV_OTP_CODE=1234` و `ENVIRONMENT=development` فقط برای توسعه‌اند. در محیط production، پیش از فعال‌سازی سرویس پیامک واقعی نباید مسیر ورود را در اختیار کاربر قرار دهید.

## API

همهٔ مسیرها با `/api/v1` شروع می‌شوند. برای مسیرهای محافظت‌شده این header را بفرستید:

```http
Authorization: Bearer <access_token>
```

| مسیر | احراز هویت | کاربرد |
|---|---:|---|
| `POST /auth/request-code` | خیر | ساخت چالش ورود برای `mobile` |
| `POST /auth/verify` | خیر | تأیید `mobile` و `code`، ایجاد/بازیابی کاربر و بازگرداندن tokenها |
| `POST /auth/refresh` | خیر | چرخش access و refresh token |
| `POST /auth/logout` | بله | ابطال نشست جاری؛ پاسخ `204` |
| `GET /users/me` | بله | دریافت پروفایل جاری |
| `PATCH /users/me` | بله | تغییر اختیاری `email` و `username` |
| `POST /contracts/extract` | بله | ارسال multipart با فیلد `file` از نوع PDF یا DOCX؛ استخراج، تفکیک و دسته‌بندی |
| `POST /contracts/classify` | بله | دسته‌بندی فهرست بندهای JSON |
| `POST /contracts/chunk` | بله | چانک‌سازی بندهای ورودی؛ این مسیر چانک‌ها را ذخیره نمی‌کند |
| `POST /contracts/embed-chunk` | بله | ساخت embedding برای یک چانک و upsert آن برای کاربر جاری |
| `POST /contracts/search` | بله | جست‌وجوی معنایی بین embeddingهای همان کاربر |

نمونهٔ دسته‌بندی:

```json
{
  "clauses": [
    {
      "clause_id": "1",
      "index": 1,
      "article_title": "ماده ششم - مبلغ قرارداد",
      "text": "پرداخت اقساط طبق توافق انجام می‌شود."
    }
  ]
}
```

برای ذخیره و سپس جست‌وجوی یک چانک:

```json
POST /api/v1/contracts/embed-chunk
{"contract_id":"contract-1","chunk_id":"chunk-1","text":"پرداخت اقساط طبق توافق انجام می‌شود."}

POST /api/v1/contracts/search
{"query":"شرایط پرداخت قرارداد چیست؟","top_k":5}
```

`top_k` بین ۱ تا ۱۰۰ است (کلید `limit` نیز پذیرفته می‌شود). مقدار `similarity` امتیاز شباهت کسینوسی است، نه احتمال یا نمرهٔ حقوقی. جست‌وجو به بردارهای ۳۸۴بعدی وابسته است؛ ناسازگاری ابعاد پاسخ ۵۰۰ و در دسترس نبودن مدل یا پایگاه داده پاسخ ۵۰۳ می‌دهد.

## جریان پردازش قرارداد

1. ورودی multipart با سقف حجم خوانده می‌شود و PDF/DOCX با نوع اعلام‌شده و امضای فایل بررسی می‌شود.
2. متن از PDF با `pypdf` و از DOCX با `python-docx` استخراج می‌شود؛ DOCX از نظر محدودیت‌های ZIP نیز کنترل می‌شود.
3. بخش پایانی و امضا تا حد امکان جدا، متن نرمال و بندها همراه عنوان ماده تفکیک می‌شوند.
4. دسته‌بندی قانون‌محور ابتدا اجرا می‌شود. در صورت لزوم gateway اختیاری LLM فراخوانی می‌شود و برای هر بند `taxonomy` و `search_context` تولید می‌شود.
5. برای جست‌وجوی معنایی، خروجی بندها را ابتدا به `/contracts/chunk` و سپس هر قطعه را به `/contracts/embed-chunk` بفرستید. اتصال خودکار استخراج به ذخیره‌سازی embedding هنوز وجود ندارد.

متن قرارداد و نتیجهٔ استخراج در مسیر فعلی به‌صورت خودکار در پایگاه داده، فایل یا Redis ذخیره نمی‌شود؛ با این حال، متن چانک ارسالی به `embed-chunk` در جدول embedding نگهداری می‌شود. اگر LLM دسته‌بندی فعال باشد، عنوان و بخش محدودی از متن بند به سرویس پیکربندی‌شده ارسال می‌شود؛ سیاست نگه‌داری دادهٔ آن سرویس را جداگانه بررسی کنید.

## داده و migration

اجرای `python -m contract_guard.infrastructure.database.migrate` فایل‌های SQL شماره‌دار `001` تا `005` را به‌ترتیب اجرا می‌کند. آن‌ها کاربران/نشست‌ها و جدول `contract_embeddings` با شاخص HNSW و `vector(384)` را آماده می‌کنند.

در `migrations/versions/` یک migration جداگانهٔ Alembic برای جدول `legal_knowledge_base` وجود دارد. این migration در runner SQL بالا اجرا نمی‌شود و Alembic نیز وابستگی نصب‌شدهٔ پروژه نیست؛ بنابراین آن را بخشی از راه‌اندازی معمول تلقی نکنید تا زمانی که فرایند migration یکپارچه شود. اسکریپت `python -m scripts.seed_legal_kb` نیز به همان جدول نیاز دارد و فعلاً رکوردها را بدون embedding می‌سازد.

## آزمون

```powershell
python -m pytest -q
```

آزمون‌های واحد دسته‌بندی، چانک‌سازی، ذخیرهٔ embedding، احراز هویت endpointها و جست‌وجوی محدود به مالک را پوشش می‌دهند. آزمون‌های integration جست‌وجو به صورت پیش‌فرض skip می‌شوند و به متغیرهای زیر نیاز دارند:

```powershell
$env:TEST_DATABASE_URL = "postgresql://.../contract_guard_search_test_..."
$env:RUN_REAL_EMBEDDING_TEST = "1" # فقط برای آزمون مدل واقعی
python -m pytest tests/test_semantic_search_integration.py -q
```

این آزمون‌ها را فقط با پایگاه دادهٔ تست اختصاصی اجرا کنید؛ آزمون مدل واقعی دانلود/بارگذاری مدل را انجام می‌دهد.

## محدودیت‌های شناخته‌شده و گام‌های بعدی

- PDF اسکن‌شدهٔ فاقد لایهٔ متن به OCR نیاز دارد و هنوز پشتیبانی نمی‌شود.
- تشخیص امضا، تفکیک بندها، اصلاح شماره‌ها و قواعد دسته‌بندی قطعی نیستند و باید با مجموعهٔ مستقل قراردادهای برچسب‌خورده ارزیابی شوند.
- امتیاز `confidence=0.9` قانون‌محور، احتمال آماری کالیبره‌شده نیست.
- ذخیرهٔ قرارداد، اتصال خودکار استخراج به چانک/embedding، بازیابی دانش حقوقی و RAG هنوز کامل نیستند.
- تحلیل ریسک، گزارش نهایی، سرویس پیامک، مشاهده‌پذیری و طراحی عملیاتی production باقی مانده‌اند.

## ساختار مهم پروژه

```text
src/contract_guard/
├── application/services/          # chunking، embedding و semantic search
├── application/use_cases/         # ورود، استخراج و دسته‌بندی
├── infrastructure/database/       # اتصال، migration SQL و repositoryها
├── infrastructure/parsers/        # PDF، DOCX و worker استخراج
└── infrastructure/web/            # FastAPI، وابستگی احراز هویت و endpointها
migrations/                        # migrationهای SQL شماره‌دار و migration Alembic جداگانه
scripts/seed_legal_kb.py           # دادهٔ آغازین گزیدهٔ قوانین
tests/                              # آزمون‌های واحد و integration
```
