# گزارش فنی Contract Guard

این سند وضعیت فعلی کد پروژه، راه‌اندازی و مسئولیت توابع را توضیح می‌دهد. کد فعلی دریافت قرارداد، تفکیک و دسته‌بندی بندها و ورود با شماره موبایل را فراهم می‌کند. بازیابی قوانین، تحلیل ریسک و تولید گزارش نهایی هنوز کامل نشده‌اند.

## راه‌اندازی در ویندوز

پیش‌نیازها: Python 3.11 یا بالاتر، PostgreSQL، Redis و در صورت استفاده از فایل Compose، Docker. در ریشه پروژه:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\venv\Scripts\python.exe -m pip install -e .
docker compose up -d postgres redis
.\venv\Scripts\python.exe -m contract_guard.infrastructure.database.migrate
.\venv\Scripts\python.exe -m contract_guard
```

اگر محیط مجازی وجود ندارد، ابتدا `python -m venv venv` را اجرا کنید. مقادیر اتصال `.env` باید با سرویس‌ها هماهنگ باشند. اگر پایگاه داده موجود دارید، مقادیر آن را بدون بررسی جایگزین نکنید. رابط آزمایشی FastAPI در `/docs` در دسترس است. نقطه ورود فعلی `python -m contract_guard` است؛ دستور قدیمی `uvicorn app.main:app` به ساختار فعلی اشاره نمی‌کند.

## تنظیمات

تمام تنظیمات الزامی برنامه از متغیر محیطی یا فایل `.env` با Pydantic Settings خوانده و اعتبارسنجی می‌شوند. نمونه در `.env.example` است. این فایل حاوی مقادیر توسعه است؛ اطلاعات محرمانه واقعی را در مخزن قرار ندهید.

| گروه | متغیرها | کاربرد |
|---|---|---|
| محیط | `ENVIRONMENT`, `HOST`, `PORT` | نوع محیط و آدرس و درگاه برنامه |
| PostgreSQL | `DATABASE_URL`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | اتصال برنامه و تنظیم سرویس Compose |
| Redis | `REDIS_URL`, `REDIS_PORT`, `REDIS_KEY_PREFIX`, `REDIS_SOCKET_TIMEOUT_SECONDS` | اتصال و فضای نام چالش‌های ورود |
| ورود | `SESSION_HOURS`, `ACCESS_TOKEN_MINUTES`, `OTP_MINUTES`, `OTP_MAX_ATTEMPTS`, `OTP_REQUEST_COOLDOWN_SECONDS`, `DEV_OTP_CODE` | عمر سشن و توکن، انقضا و محدودیت کد آزمایشی |
| استخراج | `UPLOAD_MAX_BYTES`, `EXTRACTION_TIMEOUT_SECONDS`, `EXTRACTION_MAX_PAGES`, `EXTRACTION_MAX_CHARS` | محدودیت حجم، زمان و اندازه متن و صفحات |
| DOCX | `DOCX_MAX_ENTRIES`, `DOCX_MAX_UNCOMPRESSED_BYTES`, `DOCX_MAX_COMPRESSION_RATIO` | محدودیت‌های محتوای ZIP سند |
| مدل اختیاری | `TAXONOMY_LLM_URL`, `TAXONOMY_LLM_MODEL`, `TAXONOMY_LLM_API_KEY`, `TAXONOMY_LLM_TIMEOUT_SECONDS`, `TAXONOMY_LLM_MAX_CHARS`, `TAXONOMY_LLM_CONCURRENCY` | نشانی کامل Chat Completions، نام مدل، کلید و محدودیت فراخوانی |

`ENVIRONMENT=development` و کد ثابت `1234` صرفاً برای توسعه‌اند. در محیط production تا اتصال سرویس پیامک، درخواست و تأیید ورود با خطای 503 متوقف می‌شوند.

## API و ترتیب آزمایش

همه مسیرها پیشوند `/api/v1` دارند. برای مسیرهای محافظت‌شده از `Authorization: Bearer <access_token>` استفاده کنید.

| متد و مسیر | ورودی / کار |
|---|---|
| `POST /auth/request-code` | `{"mobile":"09123456789"}`؛ ساخت چالش با محدودیت درخواست |
| `POST /auth/verify` | `{"mobile":"09123456789","code":"1234"}`؛ تأیید کد آزمایشی و ساخت کاربر و سشن |
| `POST /auth/refresh` | `{"refresh_token":"..."}`؛ تعویض هر دو توکن |
| `POST /auth/logout` | ابطال سشن جاری؛ پاسخ 204 |
| `GET /users/me` | اطلاعات پروفایل کاربر جاری |
| `PATCH /users/me` | تغییر اختیاری `email` و `username` |
| `POST /contracts/extract` | یک فیلد multipart به نام `file` با نوع PDF یا DOCX؛ استخراج و دسته‌بندی |
| `POST /contracts/classify` | دریافت JSON فهرست بندها و برگرداندن دسته‌بندی آنها |

ابتدا کد درخواست و تأیید شود؛ سپس access token را در بخش Authorize رابط `/docs` وارد کنید. کدهای عددی فارسی و عربی شماره موبایل در اعتبارسنجی به رقم انگلیسی تبدیل می‌شوند. نمونه ورودی دسته‌بندی:

```json
{"clauses":[{"clause_id":"1","index":1,"article_title":"ماده ششم - مبلغ قرارداد","text":"پرداخت اقساط طبق توافق انجام می‌شود."}]}
```

خروجی استخراج شامل `text` کامل اولیه، `closing_metadata`، تعداد و فهرست `clauses` است. هر بند شامل شناسه، شماره، متن، عنوان ماده، `taxonomy` و `search_context` است؛ اگر اصلاح شماره با شواهد کافی انجام شود، متن پیش از اصلاح در `original_text` می‌آید.

## استراتژی ورود و ذخیره‌سازی

- شماره موبایل و اطلاعات اختیاری پروفایل در PostgreSQL و وضعیت سشن و هش توکن‌های تصادفی در جدول سشن نگهداری می‌شود. توکن‌ها JWT نیستند.
- Redis برای چالش کوتاه‌عمر، شمارش تلاش و فاصله مجاز بین درخواست‌ها به کار می‌رود. عملیات مربوطه با اسکریپت Lua به‌صورت اتمی انجام می‌شوند. تنظیم Compose داده Redis را پایدار نمی‌کند.
- refresh توکن‌های دسترسی و refresh را هم‌زمان تغییر می‌دهد؛ توکن‌های قبلی پس از آن معتبر نیستند. عمر کل سشن با refresh تمدید نمی‌شود و حداکثر 24 ساعت است. logout آن را باطل می‌کند.
- مهاجرت‌های SQL در `migrations/001_create_users.sql` تا `003_refresh_tokens.sql` قرار دارند؛ دستور مهاجرت آنها را به ترتیب اجرا می‌کند. این سازوکار یک رانر ساده SQL است، نه Alembic.

## خط لوله قرارداد و حریم خصوصی

1. ورودی multipart به‌صورت جریانی با محدودیت حجم خوانده می‌شود و پارسر جداگانه‌ای برای پردازش فایل در فرایند فرزند و با مهلت زمانی اجرا می‌شود.
2. نوع اعلام‌شده با امضای فایل بررسی می‌شود. PDF با pypdf و DOCX با python-docx استخراج می‌شود. DOCX از نظر اندازه آرشیو و محتوای نامناسب نیز بررسی می‌شود.
3. متن پایانی و امضا با قواعد تشخیصی از متن مورد استفاده برای تفکیک جدا و در `closing_metadata` برگردانده می‌شود. `text` سطح سند همچنان متن کامل استخراج‌شده است.
4. حروف و ارقام لازم نرمال می‌شوند؛ ماده‌ها و بندهای شماره‌دار تفکیک و عنوان ماده به هر بند الصاق می‌شود. اصلاح اعداد مشکوک فقط در شرایط دارای قرینه انجام می‌شود و تشخیص آن قطعی نیست.
5. موتور قواعد ابتدا دسته را تعیین می‌کند؛ در صورت نبود تصمیم قطعی، درگاه مدل اختیاری فراخوانی می‌شود. در نهایت `search_context` از عنوان، نام فارسی دسته و متن بند ساخته می‌شود.

برنامه متن قرارداد و خروجی پردازش را عمداً در پایگاه داده، فایل یا Redis ذخیره نمی‌کند. پاسخ API و متغیرهای پردازش حاوی متن هستند و نحوه نگهداری توسط کلاینت، پراکسی، سیستم‌عامل و ارائه‌دهنده مدل خارج از این تضمین است. در صورت فعال‌کردن مدل، عنوان و بخش محدودی از متن بند به نشانی تنظیم‌شده ارسال می‌شود و سیاست نگهداری آن سرویس باید جداگانه بررسی شود.

## طبقه‌بندی و نقش مدل

مدل زبانی برای راه‌اندازی اجباری نیست. قواعد کلیدواژه و عنوان، بندهای شناخته‌شده را با `source=rule_based` دسته‌بندی می‌کنند. موتور از 12 دسته پشتیبانی می‌کند:

`financial`, `penalty_compensation`, `intellectual_property`, `confidentiality`, `termination`, `scope_delivery`, `warranty_support`, `dispute_resolution`, `force_majeure`, `general_legal`, `non_compete`, `sla_obligations`.

برای موارد مبهم می‌توان بعداً مدل سازگار با Chat Completions را تنظیم کرد؛ در تنظیم نمونه نام و نشانی مدل خالی و فراخوانی غیرفعال است. اگر مدل پیکربندی نشده باشد یا خطا دهد، خروجی `general_legal` با `confidence=0` و `degraded=true` است. در این حالت `source=llm` مسیر fallback را نشان می‌دهد و به معنی اجرای موفق مدل نیست. `confidence=0.9` قواعد تخمینی است، نه احتمال آماری کالیبره‌شده. بدون ارزیابی روی داده‌های برچسب‌خورده نمی‌توان دقت 90 درصد یا مناسب‌بودن قواعد برای همه قراردادها را تضمین کرد.

## ساختار پوشه‌ها

```text
contract-guard/
├── .env.example, pyproject.toml, Dockerfile, docker-compose.yml
├── README.md
├── migrations/                 مهاجرت‌های SQL
├── src/contract_guard/
│   ├── config/                 تنظیمات
│   ├── domain/                 مدل‌ها، خطاها و قراردادهای انتزاعی
│   ├── application/
│   │   ├── ports/             قرارداد کلاسیفایر و درگاه مدل
│   │   ├── dtos/              جایگاه رزروشده DTO
│   │   └── use_cases/         ورود، تفکیک، دسته‌بندی و پردازش
│   └── infrastructure/
│       ├── cache/             چالش Redis
│       ├── database/          اتصال و مهاجرت PostgreSQL
│       ├── llm/               درگاه اختیاری مدل
│       ├── parsers/           PDF، DOCX و فرایند استخراج
│       ├── vector_store/      جایگاه رزروشده بازیابی برداری
│       └── web/               FastAPI، اعتبارسنجی و مسیرها
├── tests/unit/                تست‌های فعلی
├── graft/                     گراف راهنمای کد
└── openspec/                  مستندات و طرح‌های موجود
```

برخی فایل‌ها صرفاً placeholder هستند: `application/dtos/*`، `analyze_clause.py`، `generate_report.py`، `config/logging.py`، `infrastructure/vector_store/*`، `llm/lite_llm_client.py` و فایل‌های prompts، `database/base_model.py`، مخزن دانش حقوقی، `parsers/normalizer.py`، `web/middlewares.py`، `web/error_handlers.py` و endpoint `analysis.py`. این نام‌ها به معنی پیاده‌سازی RAG، لاگ ساختاریافته یا تحلیل ریسک نیستند. endpoint فعال استخراج `web/v1/endpoints/ingestion.py` است.

## فهرست مسئولیت توابع

هر ردیف به فایل زیر `src/contract_guard` اشاره می‌کند؛ متدهای یک کلاس کنار هم آمده‌اند. توابع هماهنگ‌کننده طبیعتاً چند مرحله را فراخوانی می‌کنند و همه آنها هنوز به توابع تک‌وظیفه‌ای کوچک‌تر تفکیک نشده‌اند.

| فایل و تابع | مسئولیت فعلی |
|---|---|
| `__main__.main` | بارگذاری تنظیمات و اجرای Uvicorn |
| `application/ports/clause_classifier.classify_batch` | قرارداد دسته‌بندی گروهی ناهمگام |
| `application/ports/taxonomy_gateway.classify` | قرارداد دسته‌بندی یک بند از طریق درگاه |
| `application/use_cases/classify_clauses.HybridClauseClassifier.__init__` | نگهداری درگاه و محدودکننده هم‌زمانی |
| `application/use_cases/classify_clauses.HybridClauseClassifier.classify_batch` و تابع داخلی `classify` | اجرای قواعد و fallback هر بند و جمع‌آوری نتایج |
| `application/use_cases/clause_splitter.segment_clauses` | نرمال‌سازی و تفکیک متن و انتساب ماده والد |
| `application/use_cases/extract_closing.extract_closing` | جداسازی تقریبی بخش امضا و خاتمه |
| `application/use_cases/extract_document.extract_document` | اجرای فرایند استخراج و تبدیل خطا به پاسخ HTTP |
| `application/use_cases/ingest_contract.ingest_contract` | استخراج با اینترفیس داده‌شده و ساخت مدل قرارداد؛ مسیر مستقل از endpoint فعلی |
| `application/use_cases/normalize_clause_numbers.normalize_clause_numbers` | اصلاح محتاطانه شماره‌ها و ارجاعات بر اساس قرینه |
| `application/use_cases/taxonomy_rules.normalize` | نرمال‌سازی متن برای تطبیق قواعد |
| `application/use_cases/taxonomy_rules.classify_rule` | تطبیق نشانه‌ها، انتخاب دسته اصلی و دسته‌های فرعی |
| `application/use_cases/search_context.search_context` | ساخت رشته بافت جست‌وجو از عنوان، دسته و متن |
| `application/use_cases/request_login.request_login` | کنترل محیط توسعه و ساخت چالش ورود |
| `application/use_cases/verify_login.verify_login` | مصرف چالش، ساخت یا بازیابی کاربر و ایجاد سشن و توکن‌ها |
| `application/use_cases/refresh_session.refresh_session` | اعتبارسنجی refresh و چرخش توکن‌ها در تراکنش |
| `application/use_cases/logout.logout` | ثبت ابطال سشن |
| `application/use_cases/update_profile.update_profile` | اعمال تغییرات پروفایل در پایگاه داده |
| `domain/models/taxonomy.Classification.unique_categories` | جلوگیری از تکرار دسته اصلی و فرعی |
| `domain/ports/text_extractor.extract`، `vector_store.search`، `llm_provider.generate`، `audit_repo.record` | امضای انتزاعی قابلیت‌ها؛ خودشان پیاده‌سازی بیرونی نیستند |
| `infrastructure/cache/challenge_keys.challenge_keys` | ساخت کلیدهای Redis مبتنی بر هش شماره |
| `infrastructure/cache/create_challenge.create_challenge` | ایجاد چالش و اعمال فاصله درخواست |
| `infrastructure/cache/consume_challenge.consume_challenge` | بررسی و مصرف اتمی کد و محدودیت تلاش |
| `infrastructure/cache/redis_client.redis_client` | ساخت کلاینت Redis |
| `infrastructure/database/session.database` | ایجاد اتصال PostgreSQL برای استفاده در context manager |
| `infrastructure/database/migrate.migrate` | خواندن و اجرای مرتب فایل‌های SQL مهاجرت |
| `infrastructure/llm/taxonomy_gateway.LLMTaxonomyGateway.classify` | درخواست ناهمگام مدل اختیاری و اعتبارسنجی پاسخ |
| `infrastructure/parsers/select_parser.select_parser` | انتخاب پارسر مطابق نوع و امضای فایل |
| `infrastructure/parsers/pdf_parser.PdfParser.extract` | خواندن و کنترل PDF و استخراج متن |
| `infrastructure/parsers/docx_parser.DocxParser.extract` | کنترل آرشیو DOCX و استخراج پاراگراف‌ها و جدول‌ها |
| `infrastructure/parsers/extraction_worker.main` | دریافت داده، اجرای پارسر و تولید خروجی پردازش در فرایند فرزند |
| `infrastructure/web/dependencies.current_session` | اعتبارسنجی access token و بازگرداندن کاربر و سشن |
| `infrastructure/web/schemas.MobileRequest.validate_mobile` | نرمال‌سازی و اعتبارسنجی شماره موبایل |
| `infrastructure/web/schemas.ProfileUpdate.validate_email` | اعتبارسنجی قالب ایمیل اختیاری |
| `infrastructure/web/v1/endpoints/request_login.request_code`، `verify_login.verify_code`، `refresh.refresh`، `logout.logout_session` | اتصال مسیرهای احراز هویت به سناریوهای متناظر |
| `infrastructure/web/v1/endpoints/profile.profile`، `update_profile.profile_update` | نمایش و ویرایش پروفایل |
| `infrastructure/web/v1/endpoints/taxonomy.classify_contract` | پذیرش بندها و اجرای دسته‌بندی گروهی |
| `infrastructure/web/v1/endpoints/ingestion.extract_contract` | دریافت محدود multipart، اجرای استخراج و افزودن دسته و بافت؛ شامل callbackهای داخلی `part_begin`، `header_field`، `header_value`، `header_end`، `headers_finished`، `part_data` و `finished` برای مراحل خواندن multipart |

مدل‌های Pydantic در `web/schemas.py` و `domain/models/taxonomy.py` ورودی و خروجی‌ها را اعتبارسنجی می‌کنند. سایر مدل‌ها و enumها در `domain/models/` قرار دارند. فایل‌های `__init__.py` عمدتاً نشانگر بسته‌اند.

## آزمون و محدودیت‌های شناخته‌شده

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests/unit -v
```

تست‌های موجود قواعد، حالت fallback، جداسازی امضا، نمونه پردازش DOCX و برخی خطاها را بررسی می‌کنند؛ برای سنجش دقت واقعی، تست فایل‌های متنوع PDF و DOCX فارسی و مجموعه مستقل برچسب‌خورده لازم است. استخراج متن PDF اسکن‌شده بدون متن قابل انتخاب به OCR نیاز دارد که پیاده‌سازی نشده است. دقت استخراج امضا و شماره‌ها نیز تضمین مطلق ندارد.

معماری در حال گذار است: برخی use caseها مستقیم به FastAPI، PostgreSQL یا Redis وابسته‌اند و جداسازی کامل Clean Architecture، اتصال سرویس پیامک، RAG/pgvector، تحلیل ریسک، گزارش نهایی و طراحی عملیاتی production هنوز نیاز به کار دارند.

