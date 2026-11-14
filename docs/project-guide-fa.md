# راهنمای جامع فنی Contract Guard

مبنای سند: کد موجود در فضای کاری در ۱۱ نوامبر ۲۰۲۶. این سند وضعیت پیاده‌سازی را از طرح‌ها جدا می‌کند؛ برای رفتار دقیق هر تابع، فایل نام‌برده مرجع نهایی است. تغییرات محلی ثبت‌نشده نیز در بررسی لحاظ شده‌اند. مقادیر محرمانه فایل `.env` در این سند درج نشده‌اند.

## ۱. معرفی و وضعیت محصول

Contract Guard یک بک‌اند Python/FastAPI برای دریافت قرارداد فارسی، استخراج و قطعه‌بندی متن، دسته‌بندی بندها و جستجوی معنایی چانک‌های ذخیره‌شده هر کاربر است. ورود با شماره موبایل در حالت توسعه و نشست Bearer پیاده‌سازی شده است. استخراج PDF اسکن‌شده با OCR، تحلیل ریسک، تولید گزارش نهایی و پاسخ RAG انتهابه‌انتها در مسیر فعال فعلی پیاده‌سازی کامل ندارند.

| قابلیت | وضعیت فعلی | ملاحظات |
|---|---|---|
| ورود، پروفایل، refresh و خروج | فعال | کد ثابت فقط در توسعه؛ ارسال پیامک production موجود نیست. |
| استخراج PDF و DOCX | فعال | نیازمند متن قابل استخراج؛ کنترل اندازه و مهلت اجرا دارد. |
| تشخیص بند و دسته‌بندی | فعال | قواعد و fallback اختیاری مدل؛ دقت آماری تضمین نشده است. |
| chunk، embedding و جستجو | فعال | ذخیره و جستجوی مجزا با API؛ مالک هر ردیف تعیین می‌شود. |
| دانش حقوقی، تحلیل ریسک و گزارش | طرح یا اجزای ناقص | وجود نام فایل یا migration به معنی فعال بودن قابلیت نیست. |

## ۲. نقشهٔ اسناد و مخزن

| مسیر | نقش |
|---|---|
| `README.md` | شروع کار و گزارش قبلی؛ بخش‌هایی درباره عدم ذخیره قرارداد، نبود pgvector و migrationها با کد فعلی قدیمی‌اند. |
| `docs/semantic-search.md` | راهنمای اجرایی و آزمایش جستجوی معنایی. |
| `docs/project-guide-fa.md` | همین سند، شامل معماری و مرجع توابع. |
| `openspec/changes/contract-intake-risk-analysis/` | proposal، design، tasks و مشخصات تغییر؛ اسناد طراحی الزاماً معادل قابلیت اجراشده نیستند. |
| `graft/` | گراف و کارت‌های کد برای پیدا کردن نمادها و روابط؛ ممکن است لازم باشد به‌روز شود. |
| `.env.example`, `pyproject.toml` | نمونه تنظیمات و مشخصات بسته و وابستگی‌ها. |
| `docker-compose.yml`, `Dockerfile` | تعریف PostgreSQL/Redis محلی و تصویر سرویس. |

ساختار اصلی:

```text
src/contract_guard/
  config/                 تنظیمات
  domain/models/          مدل‌ها و قواعد داده دامنه
  domain/ports, services/ پروتکل‌ها و مرزهای انتزاعی
  application/use_cases/ سناریوهای ورود، استخراج و دسته‌بندی
  application/services/  chunking، embedding و semantic search
  infrastructure/cache/  Redis و چالش ورود
  infrastructure/database/ اتصال، migration و مخزن چانک
  infrastructure/parsers/ پردازش PDF/DOCX و worker
  infrastructure/llm/    درگاه اختیاری دسته‌بندی
  infrastructure/web/    FastAPI، dependency، schema و endpoint
migrations/               SQL و یک مسیر Alembic مجزا
tests/                    آزمون واحد، API و integration
scripts/                  اسکریپت‌های کمکی
```

## ۳. معماری و الگوها

- router نسخه‌دار با پیشوند `/api/v1` ماژول‌های endpoint را ثبت می‌کند. `app.py` شیء FastAPI را می‌سازد و `__main__.py` با Uvicorn اجرا می‌کند.
- Pydantic ورودی و خروجی، محدودیت‌ها و بخشی از OpenAPI را تعریف می‌کند. وابستگی `current_session` در FastAPI دسترسی را بررسی می‌کند. نمونه‌های Swagger در `/docs` و قرارداد در `/openapi.json` هستند.
- سرویس جستجو به پروتکل embedding و مخزن متکی است؛ repository، SQL پارامتری و psycopg را مدیریت می‌کند. `LocalEmbeddingService` مدل را با lock به‌صورت lazy و یک‌بار در هر process بارگذاری می‌کند.
- پروژه از لایه‌های شبیه ports-and-adapters استفاده می‌کند، اما جداسازی کامل نیست: برخی use caseها مستقیماً به FastAPI، Redis یا دیتابیس وابسته‌اند و endpointها برخی dependencyها را مستقیم می‌سازند.
- اتصال PostgreSQL هم‌زمان است. endpointهای هم‌زمان در threadpool FastAPI اجرا می‌شوند؛ دسته‌بندی و دریافت فایل مسیرهای async دارند. نباید کار CPU سنگین یا psycopg هم‌زمان مستقیماً در event loop افزوده شود.
- تنظیمات با `pydantic-settings` از محیط و `.env` خوانده می‌شوند. `extra="ignore"` متغیرهای ناشناخته را در مدل نادیده می‌گیرد.

## ۴. جریان‌های اصلی

### ورود و کنترل دسترسی

1. `POST /auth/request-code` در محیط توسعه چالش Redis با TTL و فاصله درخواست ایجاد می‌کند؛ Lua عملیات را اتمی می‌کند.
2. `POST /auth/verify` کد توسعه را با مقایسه امن و شمارش تلاش بررسی می‌کند؛ کاربر و login session در PostgreSQL ساخته یا بازیابی می‌شوند.
3. access و refresh توکن تصادفی‌اند، JWT نیستند و هش SHA-256 آنها ذخیره می‌شود. `current_session` هش access token، انقضا و عدم ابطال را بررسی می‌کند.
4. refresh هر دو توکن را می‌چرخاند و عمر کلی session را افزایش نمی‌دهد؛ logout session را باطل می‌کند.
5. در production درخواست و تأیید ورود تا اتصال سرویس پیامک خطای 503 دارند. Redis در Compose بدون persistence پیکربندی شده است.

### دریافت و استخراج قرارداد

`extract_contract` محتوای multipart را با محدودیت حجم می‌خواند؛ پردازش در فرایند فرزند و با timeout انجام می‌شود. انتخاب پارسر علاوه بر نوع اعلام‌شده، امضای PDF/DOCX را کنترل می‌کند. پارسر PDF فایل رمزگذاری‌شده، متن خالی و بیش از حد بزرگ یا پرصفحه را رد می‌کند. پارسر DOCX محتویات ZIP، رمزگذاری، مسیرها، فایل اجرایی/ماکرو، embedding و نسبت فشرده‌سازی را کنترل می‌کند و پاراگراف و جدول را می‌خواند.

سپس بخش پایانی احتمالی امضا از متن قطعه‌بندی جدا، متن به بند و ماده تقسیم، شماره‌های مشکوک با قواعد محتاطانه بررسی و بندها دسته‌بندی می‌شوند. نتیجه شامل متن و متادیتای بندها است. این عملیات با OCR یا بازبینی حقوقی انسانی معادل نیست.

### طبقه‌بندی و chunking

موتور قواعد ابتدا دسته را از نشانه‌های متن و عنوان حدس می‌زند. برای موارد نامشخص درگاه اختیاری LLM با کنترل هم‌زمانی فراخوانی می‌شود؛ نبود تنظیمات یا خطا می‌تواند خروجی degraded با `general_legal` تولید کند. confidence خروجی قواعد احتمال کالیبره‌شده نیست. درگاه اختیاری ممکن است عنوان و بخشی از متن را به سرویس تنظیم‌شده ارسال کند.

`ClauseChunker` هر بند را به پنجره‌های حداکثر ۸۰۰ نویسه با هم‌پوشانی ۱۵۰ نویسه تقسیم می‌کند و در صورت امکان مرز کلمه را انتخاب می‌کند. metadata از بند به چانک منتقل می‌شود. `chunk_index` پی‌درپی و مربوط به خروجی یک درخواست است؛ chunk endpoint خودکار embedding را ذخیره نمی‌کند.

### ذخیره و جستجوی برداری

کلاینت متن و شناسه هر چانک را جداگانه به `embed-chunk` می‌دهد. مدل `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` با revision پیش‌فرض `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` بردار ۳۸۴بعدی می‌سازد. repository با کلید `(user_id, contract_id, chunk_id)` درج یا محتوا و بردار موجود را به‌روزرسانی می‌کند. محتوای این endpoint در دیتابیس ذخیره می‌شود؛ ادعای قدیمی README مبنی بر عدم ذخیره متن دیگر برای این مسیر صحیح نیست.

برای جستجو متن سؤال به همان سرویس embedding می‌رود؛ تعداد ابعاد بررسی می‌شود. SQL با پارامتر و شرط `user_id`، فاصله کسینوسی pgvector را محاسبه و نتایج را از نزدیک‌ترین مرتب می‌کند. `similarity = 1 - cosine_distance` است، احتمال نیست. داده نبودن پاسخ `[]` می‌دهد. نام و revision مدل تولیدکنندهٔ ردیف‌های قدیمی در جدول ثبت نشده‌اند؛ فقط ۳۸۴بعدی بودن، یکسان بودن منشأ را اثبات نمی‌کند.

## ۵. فهرست API فعال

تمام مسیرهای جدول با `/api/v1` آغاز می‌شوند. همهٔ مسیرهای قرارداد و پروفایل و logout به access token نیاز دارند.

| متد و مسیر | کار و ورودی اصلی |
|---|---|
| `POST /auth/request-code` | شماره `mobile` و ایجاد چالش ورود. |
| `POST /auth/verify` | `mobile` و `code`؛ ساخت session و بازگرداندن توکن‌ها. |
| `POST /auth/refresh` | `refresh_token`؛ چرخش توکن. |
| `POST /auth/logout` | ابطال session جاری؛ پاسخ 204. |
| `GET /users/me` | اطلاعات کاربر جاری. |
| `PATCH /users/me` | تغییر پروفایل؛ ایمیل و نام کاربری. |
| `POST /contracts/extract` | فایل multipart با نام `file`؛ استخراج، تفکیک و دسته‌بندی. |
| `POST /contracts/classify` | دسته‌بندی فهرست `clauses`، حداکثر ۵۰۰ مورد. |
| `POST /contracts/chunk` | `contract_id` و حداکثر ۵۰۰ بند؛ خروجی چانک بدون ذخیره خودکار. |
| `POST /contracts/embed-chunk` | `contract_id`, `chunk_id`, `text`؛ ذخیره متن و بردار برای کاربر. |
| `POST /contracts/search` | `query` غیرخالی و `top_k` از ۱ تا ۱۰۰؛ `limit` نام سازگار قبلی است. |

نمونه جستجو پس از ورود و Authorize در Swagger:

```json
{"query":"شرایط پرداخت قرارداد چیست؟","top_k":5}
```

```json
[{"contract_id":"contract-1","chunk_id":"chunk-1","content":"پرداخت در سه قسط انجام می‌شود.","similarity":0.82}]
```

کدهای مهم جستجو: 401 نشست نامعتبر، 422 ورودی نامعتبر، 500 ابعاد ناسازگار و 503 خطای وابستگی. نمونه امتیاز صرفاً نمایشی است. برای قرارداد دقیق و دیگر محدودیت‌ها از `/openapi.json` استفاده کنید.

## ۶. داده و migration

| جدول/مهاجرت | نقش |
|---|---|
| `001_create_users.sql` | کاربران، شناسه UUID و موبایل یکتا. |
| `002_auth_sessions.sql` | ستون‌های پروفایل، چالش‌های SQL و sessionها؛ چالش فعال ورود در Redis است. |
| `003_refresh_tokens.sql` | هش refresh و انقضای access. |
| `004_create_contract_embeddings.sql` | جدول `contract_embeddings` و ایندکس HNSW cosine اولیه؛ تعریف اولیه بردار ۱۵۳۶بعدی است. |
| `005_local_contract_embeddings.sql` | در صورت امکان تبدیل به ۳۸۴ بعد، افزودن `chunk_id`، کلید یکتا و ایندکس cosine؛ اگر بردار ناسازگار موجود باشد تبدیل را متوقف می‌کند. |
| `migrations/versions/...py` | migration مستقل Alembic برای `legal_knowledge_base` با بردار ۱۰۲۴بعدی؛ رانر SQL معمول آن را اجرا نمی‌کند و مسیر دانش حقوقی فعال جستجوی قرارداد نیست. |

ستون‌های جدول قرارداد شامل `id`, `user_id`, `contract_id`, `clause_category`, `chunk_index`, `content`, `metadata`, `embedding`, `created_at`, `chunk_id` هستند. در پیاده‌سازی فعلی ذخیره تک‌چانک، `chunk_index` برابر صفر قرار می‌گیرد و category/metadata از درخواست embedding ذخیره نمی‌شوند. مالک ردیف با foreign key به کاربر متصل است. برای جدول‌های عملیاتی و ایندکس‌ها واقعیت دیتابیس هدف را مستقل بررسی کنید.

`python -m contract_guard.infrastructure.database.migrate` همه فایل‌های SQL شماره‌دار را به ترتیب اجرا می‌کند؛ این رانر ledger نسخه اجراشده ندارد. اجرای دوباره به سازگاری خود SQLها وابسته است. پیش از migration روی داده واقعی، backup و بررسی سازگاری لازم است. هیچ جدول یا volume موجودی را برای راه‌اندازی تست پاک نکنید.

## ۷. تنظیمات و اجرا

پیش‌نیازها: Python 3.11+، PostgreSQL با افزونه pgvector، Redis، وابستگی‌های پروژه و فایل‌های مدل در کش یا دسترسی به دریافت آنها. Compose از `pgvector/pgvector:pg16` و `redis:7` استفاده می‌کند؛ پورت‌ها روی loopback bind می‌شوند و volume فقط برای PostgreSQL تعریف شده است.

```powershell
python -m venv venv
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\venv\Scripts\python.exe -m pip install -e .
docker compose up -d postgres redis
.\venv\Scripts\python.exe -m contract_guard.infrastructure.database.migrate
.\venv\Scripts\python.exe -m contract_guard
```

اگر دیتابیس قبلاً داده دارد، پیش از اجرای migration ابتدا وضعیت آن را بررسی کنید. `.env.example` شامل تنظیمات توسعه است؛ رمز واقعی را در مخزن قرار ندهید. متغیرها:

| گروه | متغیرها و نقش |
|---|---|
| برنامه | `ENVIRONMENT`, `HOST`, `PORT`؛ محیط و شبکه برنامه. |
| پایگاه داده | `DATABASE_URL`؛ برای Compose نیز `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`. |
| Redis | `REDIS_URL`, `REDIS_PORT`, `REDIS_KEY_PREFIX`, `REDIS_SOCKET_TIMEOUT_SECONDS`. |
| ورود | `SESSION_HOURS`, `ACCESS_TOKEN_MINUTES`, `OTP_MINUTES`, `OTP_MAX_ATTEMPTS`, `OTP_REQUEST_COOLDOWN_SECONDS`, `DEV_OTP_CODE`. |
| استخراج | `UPLOAD_MAX_BYTES`, `EXTRACTION_TIMEOUT_SECONDS`, `EXTRACTION_MAX_PAGES`, `EXTRACTION_MAX_CHARS`. |
| ایمنی DOCX | `DOCX_MAX_ENTRIES`, `DOCX_MAX_UNCOMPRESSED_BYTES`, `DOCX_MAX_COMPRESSION_RATIO`. |
| دسته‌بندی اختیاری | `TAXONOMY_LLM_URL`, `TAXONOMY_LLM_MODEL`, `TAXONOMY_LLM_API_KEY`, `TAXONOMY_LLM_TIMEOUT_SECONDS`, `TAXONOMY_LLM_MAX_CHARS`, `TAXONOMY_LLM_CONCURRENCY`. |
| embedding | `EMBEDDING_MODEL_NAME`, `EMBEDDING_MODEL_REVISION`؛ مقدار پیش‌فرض در `config/settings.py` است. تغییر مدل/نسخه ممکن است با بردارهای قبلی ناسازگار باشد. |
| آزمون | `TEST_DATABASE_URL`, `RUN_REAL_EMBEDDING_TEST`؛ تنها برای تست‌ها، خارج از مدل تنظیمات برنامه. |

مدل در اولین استفاده هر process بارگذاری می‌شود. در یک آزمایش محلی قبلی بارگذاری سرد حدود ۱۳۰ ثانیه طول کشید؛ این عدد تضمین عملکرد سایر محیط‌ها نیست.

## ۸. مرجع توابع و متدها

مسیرهای زیر نسبت به `src/contract_guard` هستند، مگر خلاف آن ذکر شود. متدهای پروتکل فقط قراردادند و به‌تنهایی پیاده‌سازی خارجی ندارند.

### برنامه و لایه application

| فایل و نماد | مسئولیت |
|---|---|
| `__main__.main` | خواندن تنظیمات host/port و اجرای Uvicorn. |
| `application/ports/clause_classifier.ClauseClassifier.classify_batch` | قرارداد async دسته‌بندی چند بند. |
| `application/ports/taxonomy_gateway.TaxonomyGateway.classify` | قرارداد async درگاه دسته‌بندی یک بند. |
| `application/services/chunking.ClauseChunker.chunk_clauses` | تولید پنجره‌های هم‌پوشان با metadata بند. |
| `application/services/embedding._get_model` | بارگذاری تنبل و اشتراک مدل در process با lock. |
| `application/services/embedding.LocalEmbeddingService.embed_text` | تبدیل متن به فهرست float با مدل انتخاب‌شده. |
| `application/services/semantic_search.ChunkSearchRepository.search_similar_chunks` | قرارداد جستجوی محدود به شناسه کاربر. |
| `application/services/semantic_search.SemanticSearchService.__init__` | دریافت سرویس embedding و repository. |
| `application/services/semantic_search.SemanticSearchService.search` | تبدیل سؤال، کنترل ۳۸۴ بعد و واگذاری بازیابی؛ خطای ابعاد با `EmbeddingDimensionError`. |
| `application/use_cases/classify_clauses.HybridClauseClassifier.__init__` | نگهداری gateway و semaphore. |
| همان کلاس، `classify_batch` و تابع داخلی `classify` | اجرای قواعد، fallback درگاه و جمع‌آوری ناهمگام نتایج با حفظ ترتیب. |
| `application/use_cases/clause_splitter.segment_clauses` | تشخیص بندها و انتساب عنوان ماده. |
| `application/use_cases/extract_closing.extract_closing` | جداسازی تقریبی بخش پایانی/امضا. |
| `application/use_cases/extract_document.extract_document` | اجرای فرایند استخراج با timeout و تبدیل خطا. |
| `application/use_cases/ingest_contract.ingest_contract` | ساخت مدل قرارداد از extractor تزریق‌شده؛ مسیر مستقل از endpoint اصلی است. |
| `application/use_cases/normalize_clause_numbers._article_number` | تشخیص شماره ماده از عنوان. |
| همان فایل، `_record_correction` | ثبت متن و جزئیات اصلاح. |
| همان فایل، `_correct_group` | بررسی شماره‌های یک گروه و اصلاح محتاطانه. |
| همان فایل، `_correct_references` | بررسی و اصلاح ارجاعات دارای قرینه. |
| همان فایل، `normalize_clause_numbers` | گروه‌بندی، هماهنگی اصلاحات و برگرداندن گزارش آنها. |
| `application/use_cases/taxonomy_rules.normalize` | نرمال‌سازی ورودی تطبیق قواعد. |
| همان فایل، `classify_rule` | تطبیق نشانه‌ها و ساخت دسته‌بندی یا عدم تصمیم. |
| `application/use_cases/search_context.search_context` | ساخت متن بافت از عنوان، دسته فارسی و بند. |
| `request_login.request_login` | کنترل محیط و درخواست چالش Redis. |
| `verify_login.verify_login` | مصرف چالش، ایجاد/بازیابی کاربر و صدور توکن‌ها. |
| `refresh_session.refresh_session` | اعتبارسنجی refresh و چرخش تراکنشی توکن‌ها. |
| `logout.logout` | ابطال session. |
| `update_profile.update_profile` | اعمال تغییرات مجاز پروفایل. |

چهار مسیر آخر در `application/use_cases/` قرار دارند.

### Domain و قراردادها

| فایل و نماد | مسئولیت |
|---|---|
| `domain/models/taxonomy.Classification.unique_categories` | جلوگیری از تکرار دسته اصلی و فرعی. |
| `domain/ports/text_extractor.TextExtractor.extract` | قرارداد استخراج متن از bytes. |
| `domain/ports/vector_store.VectorStore.search` | قرارداد انتزاعی جستجوی مراجع حقوقی. |
| `domain/ports/llm_provider.LLMProvider.generate` | قرارداد تولید متن. |
| `domain/ports/audit_repo.AuditRepository.record` | قرارداد ثبت رویداد. |
| `domain/services/embedding.EmbeddingService.embed_text` | قرارداد تبدیل متن به بردار. |

سایر کلاس‌های `domain/models/` حامل داده قرارداد، بند، ریسک، مرجع حقوقی و taxonomy هستند. مدل‌های داده به‌تنهایی به معنی فعال بودن مسیر تحلیل ریسک یا دانش حقوقی نیستند.

### Infrastructure

| فایل و نماد | مسئولیت |
|---|---|
| `cache/challenge_keys.challenge_keys` | ساخت کلیدهای چالش و cooldown مبتنی بر هش شماره. |
| `cache/redis_client.redis_client` | ساخت کلاینت Redis با timeout تنظیم‌شده. |
| `cache/create_challenge.create_challenge` | ایجاد اتمی چالش و اعمال محدودیت فاصله درخواست. |
| `cache/consume_challenge.consume_challenge` | بررسی/مصرف چالش و محدودیت تلاش با Lua. |
| `database/session.database` | context manager اتصال psycopg با خروجی dict. |
| `database/migrate.migrate` | اجرای فایل‌های SQL شماره‌دار به ترتیب. |
| `database/repositories/contract_repo.ContractRepository.save_chunk_embedding` | کنترل ابعاد و upsert پارامتری بردار چانک. |
| همان کلاس، `search_similar_chunks` | کنترل ابعاد و limit، فیلتر مالک و مرتب‌سازی فاصله کسینوسی. |
| `llm/taxonomy_gateway.LLMTaxonomyGateway.classify` | فراخوانی async درگاه اختیاری و اعتبارسنجی پاسخ. |
| `parsers/select_parser.select_parser` | انتخاب پارسر با نوع و امضای فایل. |
| `parsers/pdf_parser.PdfParser.extract` | اعتبارسنجی و استخراج متن PDF. |
| `parsers/docx_parser.DocxParser.extract` | کنترل آرشیو DOCX و استخراج متن و جدول. |
| `parsers/extraction_worker.main` | خواندن فایل از stdin، استخراج و خروجی JSON فرایند فرزند. |
| `web/dependencies.current_session` | کنترل Bearer، هش توکن و اعتبار session. |
| `web/schemas.MobileRequest.validate_mobile` | نرمال‌سازی ارقام و اعتبارسنجی موبایل. |
| `web/schemas.ProfileUpdate.validate_email` | اعتبارسنجی ایمیل اختیاری. |
| `web/v1/endpoints/request_login.request_code` | اتصال endpoint درخواست کد به use case. |
| `web/v1/endpoints/verify_login.verify_code` | اتصال تأیید کد به use case. |
| `web/v1/endpoints/refresh.refresh` | اتصال refresh به use case. |
| `web/v1/endpoints/logout.logout_session` | خروج و پاسخ 204. |
| `web/v1/endpoints/profile.profile`, `update_profile.profile_update` | خواندن و ویرایش پروفایل. |
| `web/v1/endpoints/taxonomy.classify_contract` | اجرای دسته‌بندی ناهمگام. |
| `web/v1/endpoints/chunking.chunk_contract` | اعتبارسنجی و فراخوانی chunker. |
| `web/v1/endpoints/embedding.embed_chunk` | ساخت و ذخیره بردار چانک متعلق به کاربر جاری. |
| همان فایل، `SearchRequest.validate_query` | حذف فاصله اطراف و رد متن خالی. |
| همان فایل، `search_chunks` | اجرای جستجو و تبدیل خطاهای ابعاد و وابستگی به پاسخ عمومی. |
| `web/v1/endpoints/ingestion.extract_contract` | دریافت امن multipart، استخراج و افزودن طبقه‌بندی و بافت. |
| همان تابع، callbackهای `part_begin`, `header_field`, `header_value`, `header_end`, `headers_finished`, `part_data`, `finished` | مراحل پردازش جریانی part، header و داده multipart. |

پیشوند جدول Infrastructure برابر `src/contract_guard/infrastructure/` است. سازنده‌های معمول کلاس‌ها فقط تنظیم وابستگی‌ها را انجام می‌دهند؛ مدل‌ها و endpointها را برای جزئیات schema ببینید.

### ابزارها و migrationهای جداگانه

| فایل و نماد | مسئولیت |
|---|---|
| `scripts/seed_legal_kb.py:make_embedding` | تولید embedding در مسیر اسکریپت دانش حقوقی؛ مستقل از جریان فعال جستجوی چانک قرارداد است. |
| `scripts/seed_legal_kb.py:seed` | جریان seed دانش حقوقی؛ پیش‌نیازها و سازگاری را قبل از اجرا بررسی کنید. |
| `migrations/env.py:run_migrations_offline`, `run_migrations_online` | تنظیم context اجرای Alembic در دو حالت. |
| `migrations/versions/21bda99b36a8_create_legal_knowledge_base_table_with_.py:upgrade` | ساخت extension/table دانش حقوقی از طریق Alembic. |
| همان فایل، `downgrade` | حذف جدول دانش حقوقی؛ دستور مخرب است و نباید بدون برنامه backup اجرا شود. |

فایل‌های `__init__.py` عموماً نشانگر بسته‌اند. فایل‌های placeholder از جمله `analysis.py`, `analyze_clause.py`, `generate_report.py`, `vector_store/*`, `lite_llm_client.py`, `web/middlewares.py` و `web/error_handlers.py` نباید به‌عنوان قابلیت اجرایی کامل تلقی شوند.

## ۹. تست و عیب‌یابی

```powershell
.\venv\Scripts\python.exe -m pytest -q tests
```

برای integration دیتابیس، `TEST_DATABASE_URL` باید دیتابیس تست مستقلِ دارای migration و pgvector باشد. برای تست مدل واقعی علاوه بر آن `RUN_REAL_EMBEDDING_TEST=1` لازم است؛ نام دیتابیس باید با `contract_guard_search_test_` شروع شود. تست مدل واقعی کاربران تصادفی و چانک‌های آنها را پس از اجرا حذف می‌کند. جزئیات و دستور در `docs/semantic-search.md` آمده‌اند. تست رتبه‌بندی بردار از جدول موقت و rollback استفاده می‌کند.

در اجرای ثبت‌شده قبلی ۱۳ تست مرتبط از جمله پرس‌وجوی فارسی با مدل واقعی پاس شدند؛ آن نتیجه به معنی اجرای مجدد تست‌ها در زمان نگارش این سند یا تضمین سلامت محیط فعلی نیست. `pytest` در وابستگی‌های runtime فهرست نشده و ممکن است لازم باشد جداگانه برای توسعه نصب شود.

| نشانه | بررسی پیشنهادی |
|---|---|
| 401 | توکن access، انقضا، ابطال و دیتابیس session را بررسی کنید. |
| 429 درخواست کد | فاصله مجاز درخواست و وضعیت Redis را بررسی کنید. |
| 503 ورود | در production پیامک پیاده‌سازی نشده؛ اتصال Redis را نیز بررسی کنید. |
| 503 جستجو | لاگ سمت سرور، نصب/دسترسی مدل و PostgreSQL را بدون انتشار اطلاعات محرمانه بررسی کنید. |
| 500 ابعاد جستجو | مدل و revision تنظیم‌شده و ابعاد مورد انتظار ۳۸۴ را بررسی کنید. |
| استخراج ناموفق | MIME، امضای فایل، محدودیت‌ها و داشتن متن واقعی در PDF را بررسی کنید. |
| نتایج کم یا نامرتبط | مالک ردیف، مدل سازنده و کیفیت متن را بررسی کنید؛ شباهت احتمال نیست. |

## ۱۰. امنیت، حریم خصوصی و عملیات

متن ذخیره‌شده در `contract_embeddings` داده حساس قرارداد است؛ تنظیم مجوز دیتابیس، backup رمزگذاری‌شده، چرخه نگهداری و حذف، و جلوگیری از ثبت متن/توکن در لاگ لازم است. محدودیت جستجو با `user_id` در repository انجام می‌شود، اما سیستم مجوز اشتراک قرارداد یا نقش‌های سازمانی در این مسیر مشخص نشده است. در صورت استفاده از مدل دسته‌بندی بیرونی، جریان ارسال متن و قرارداد پردازش داده را بررسی کنید.

تغییر مدل، revision یا ابعاد می‌تواند مقایسه با بردارهای قبلی را بی‌معنی کند. ابتدا منشأ داده را شناسایی و ثبت کنید؛ بازتولید یا حذف بردارها باید با برنامه مهاجرت، backup و مجوز مالک داده انجام شود. از نمونه کد توسعه، پیکربندی production یا رمز واقعی نسازید.

## ۱۱. پیشنهادهای بهبود اولویت‌دار

1. **هویت و مجوز production:** اتصال پیامک واقعی، مدیریت نرخ در لبه، سیاست session و مدل دسترسی سازمان/اشتراک قرارداد با تست منفی.
2. **منشأ embedding:** ثبت شناسه مدل، revision و ابعاد برای هر مجموعه/بردار و طراحی مهاجرت بدون تخریب؛ ردیف‌های قدیمی فعلاً تأییدنشده‌اند.
3. **پایداری migration:** یکپارچه‌سازی مسیر SQL و Alembic، ثبت نسخه، بررسی idempotency و تست ارتقا و rollback روی نسخه‌های واقعی.
4. **کارایی و سنجش جستجو:** اندازه‌گیری `EXPLAIN ANALYZE` روی حجم واقعی؛ عبارت فعلی `ORDER BY distance + 0` ممکن است مانع استفاده مستقیم از ایندکس ANN شود. بهینه‌سازی باید با حفظ فیلتر مالک و ارزیابی recall انجام شود.
5. **چرخه ذخیره چانک:** نگهداری `chunk_index`, category و metadata واقعی، هویت پایدار چانک و API مدیریت/حذف مجاز؛ فعلاً embedding جداگانه ارسال می‌شود و index ذخیره‌شده صفر است.
6. **زمان شروع مدل:** warm-up کنترل‌شده، سنجش memory و زمان هر worker، بارگذاری خارج از event loop و محدودیت هم‌زمانی inference.
7. **مشاهده‌پذیری و خطا:** لاگ ساختاریافته بدون داده حساس، health/readiness برای وابستگی‌ها و الگوی یکدست خطا برای embed و auth.
8. **کیفیت و پوشش:** مجموعه فارسی برچسب‌خورده برای ranking و taxonomy، آزمون PDF/DOCX واقعی و اسکن‌شده، تست فشار، انزوا و migration؛ افزودن OCR فقط با نیاز مشخص.
9. **معماری و نگهداری:** تزریق dependencyها از composition root، کاهش وابستگی use case به FastAPI/DB، مدیریت چرخه اتصال و تصحیح README قدیمی.
10. **قابلیت‌های آینده:** تکمیل دانش حقوقی، تحلیل ریسک، citation و گزارش یا RAG فقط پس از تعریف قرارداد، مجوز، ارزیابی و سیاست داده جداگانه.
