# Contract Guard

بک‌اند FastAPI برای دریافت، پردازش و جست‌وجوی قراردادهای فارسی. این سامانه ابزار کمکی پردازش متن است و جایگزین مشاوره یا نظر حقوقی نیست.

## قابلیت‌های فعلی

- ورود با شمارهٔ موبایل، OTP توسعه‌ای و access/refresh tokenهای opaque؛ نه JWT.
- استخراج متن از PDF متنی و DOCX با سقف حجم، زمان، صفحه و محافظت‌های ZIP برای DOCX.
- تفکیک بندها، دسته‌بندی قانون‌محور و در صورت پیکربندی، gateway اختیاری LLM.
- نگهداری موقت قرارداد، بندها، chunkها، embeddingها و تحلیل‌ها در Redis اختصاصی.
- embedding محلی ۳۸۴بعدی و جست‌وجوی cosine با NumPy، محدود به یک قرارداد و مالک آن.
- پایگاه دانش حقوقی عمومی در PostgreSQL باقی می‌ماند؛ دادهٔ خصوصی قرارداد هرگز در PostgreSQL یا pgvector ذخیره نمی‌شود.

## معماری قراردادهای موقت

هر قرارداد با `contract_id` تصادفی ایجاد و تنها برای کاربر مالک قابل‌دسترسی است. دادهٔ قرارداد شامل متن استخراج‌شده، بندها، chunkها، embeddingها، تحلیل‌ها و زمان ایجاد/انقضا، همگی در یک رکورد JSON در Redis اختصاصی `redis-contracts` نگهداری می‌شود.

- `CONTRACT_TTL_SECONDS` حداکثر ۷۲۰۰ ثانیه است و از لحظهٔ پذیرش آپلود محاسبه می‌شود.
- خواندن، دسته‌بندی، chunkسازی، embedding و جست‌وجو TTL را تمدید نمی‌کنند.
- updateها با `WATCH`/transaction و `KEEPTTL` انجام می‌شوند؛ نتیجهٔ پردازشی که پس از حذف یا انقضا تمام شود ذخیره نمی‌شود.
- Redis برای قراردادها RDB و AOF ندارد، `noeviction` دارد و با پرشدن حافظه درخواست جدید را رد می‌کند.
- هر کاربر سقف قراردادهای فعال، هر قرارداد سقف payload و سقف chunk دارد.
- جدول تاریخی `contract_embeddings` عمداً حذف نشده است؛ کد برنامه دیگر آن را نمی‌خواند یا نمی‌نویسد. حذف جدول، backup و WAL یک عملیات جداگانه و نیازمند تأیید است.

TTL حذف منطقی Redis است؛ تضمین نمی‌کند تمام کپی‌های فیزیکی داده در RAM فوراً overwrite شوند.

## راه‌اندازی توسعه

پیش‌نیازها: Python 3.11+، Docker و Docker Compose. PostgreSQL همچنان برای کاربران، نشست‌ها و دانش حقوقی استفاده می‌شود. pgvector فقط برای دادهٔ عمومی دانش حقوقی باقی مانده است.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -m pip install --upgrade pip
python -m pip install -e .
docker compose up -d postgres redis redis-contracts
python -m contract_guard.infrastructure.database.migrate
python -m contract_guard
```

سرور نمونه روی `http://127.0.0.1:8001` و مستندات OpenAPI روی `/docs` در دسترس است.

`redis-contracts` فقط روی loopback توسعه منتشر می‌شود تا برنامه‌ای که روی host اجرا می‌شود به آن وصل شود؛ هرگز آن را روی شبکهٔ عمومی منتشر نکنید.

## تنظیمات

تمام تنظیمات از environment یا `.env` با Pydantic Settings خوانده می‌شوند. مقادیر نمونه در `.env.example` قرار دارند.

| گروه | متغیرهای مهم |
|---|---|
| PostgreSQL | `DATABASE_URL` و `POSTGRES_*` |
| Redis احراز هویت | `REDIS_URL`، `REDIS_KEY_PREFIX` و `REDIS_SOCKET_TIMEOUT_SECONDS` |
| Redis قرارداد | `CONTRACT_REDIS_URL`، `CONTRACT_REDIS_PORT` و `CONTRACT_REDIS_MAX_MEMORY` |
| محدودیت قرارداد | `CONTRACT_TTL_SECONDS`، `CONTRACT_MAX_ACTIVE_PER_USER`، `CONTRACT_MAX_PAYLOAD_BYTES`، `CONTRACT_MAX_CHUNKS` و `CONTRACT_PROCESSING_CONCURRENCY` |
| استخراج | `UPLOAD_MAX_BYTES`، `EXTRACTION_*` و `DOCX_MAX_*` |
| مدل‌ها | `EMBEDDING_MODEL_*` و `TAXONOMY_LLM_*` |

`CONTRACT_TTL_SECONDS` بیشتر از ۷۲۰۰ پذیرفته نمی‌شود. `CONTRACT_MAX_PAYLOAD_BYTES` نیز نمی‌تواند از `UPLOAD_MAX_BYTES` بیشتر باشد.

## API

همهٔ مسیرهای محافظت‌شده به این header نیاز دارند:

```http
Authorization: Bearer <access_token>
```

### قراردادهای موقت

| مسیر | کاربرد |
|---|---|
| `POST /api/v1/contracts` | آپلود multipart با فیلد `file` و ایجاد قرارداد موقت؛ پاسخ شامل `contract_id`، `expires_in` و `expires_at`. |
| `GET /api/v1/contracts/{contract_id}` | دریافت دادهٔ قرارداد و TTL باقیمانده، فقط برای مالک. |
| `DELETE /api/v1/contracts/{contract_id}` | حذف فوری قرارداد، فقط برای مالک. |
| `POST /api/v1/contracts/{contract_id}/classify` | دسته‌بندی بندهای ذخیره‌شده. |
| `POST /api/v1/contracts/{contract_id}/chunk` | chunkسازی بندهای ذخیره‌شده. |
| `POST /api/v1/contracts/{contract_id}/embed` | تولید embeddingهای chunkها، خارج از event loop و با محدودیت هم‌زمانی. |
| `POST /api/v1/contracts/{contract_id}/search` | جست‌وجوی semantic در همان قرارداد. |

نمونهٔ درخواست جست‌وجو:

```json
{"query":"شرایط فسخ قرارداد چیست؟", "top_k":5}
```

خطاهای اصلی: `401` برای احراز هویت، `404` برای قرارداد ناموجود/غیرمالک/منقضی، `413` برای حجم بیش از سقف، `422` برای ورودی یا embedding نامعتبر و `503` برای Redis ناموجود یا ظرفیت Redis.

### سازگاری مسیرهای قبلی

`POST /api/v1/contracts/extract`، `POST /api/v1/contracts/classify` و `POST /api/v1/contracts/chunk` همچنان دادهٔ ورودی را فقط در طول همان درخواست پردازش می‌کنند و آن را ذخیره نمی‌کنند.

`POST /api/v1/contracts/embed-chunk` و `POST /api/v1/contracts/search` تغییر ناسازگار پذیرفته‌شده دارند: `contract_id` اجباری است، داده فقط در Redis همان قرارداد نگهداری/جست‌وجو می‌شود، و درخواست فاقد `contract_id` با `422` رد می‌شود.

## محرمانگی و RAM-only

مسیر آپلود با stream سفارشی و `bytearray` در حافظه خوانده می‌شود و از `UploadFile`/`SpooledTemporaryFile` استفاده نمی‌کند. استخراج در subprocess با stdin انجام می‌شود؛ فایل اصلی پس از پایان درخواست نگهداری نمی‌شود.

تصویر برنامه `TMPDIR=/tmp/contract-guard` را تنظیم می‌کند. در production این مسیر را با tmpfs محدود mount کنید؛ برای نمونه:

```text
--tmpfs /tmp/contract-guard:rw,noexec,nosuid,size=128m
```

Compose فعلی فقط سرویس‌های backing را تعریف می‌کند؛ سرویس application در deployment باید tmpfs معادل داشته باشد. در Windows development این تضمین فقط با Docker یا RAM disk قابل دستیابی است. swap، core dump، backup و ثبت request body در log/APM نیز باید در سطح زیرساخت کنترل شوند.

## داده و migration

`python -m contract_guard.infrastructure.database.migrate` migrationهای SQL موجود را اجرا می‌کند. قبل از اجرای migration روی پایگاه دادهٔ موجود، backup بگیرید. هیچ migration مخربی برای حذف `contract_embeddings` همراه این تغییر اجرا نشده است.

## تست

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

تست‌های واحد کنترل مالکیت، محدودهٔ جست‌وجو، ابعاد embedding، سقف payload، انقضای حین embedding، parsing، chunking و taxonomy را پوشش می‌دهند. Integration واقعی نیازمند Redis قرارداد، PostgreSQL و مدل embedding در حال اجراست؛ آن را فقط در محیط اختصاصی تست اجرا کنید.

آخرین بررسی محلی: `27 passed, 17 subtests passed`. در این بررسی، اعتبارسنجی HTTP برای ورودی فاقد `contract_id` (`422`)، Redis قراردادِ در دسترس‌نبودنی (`503`) و فایل نامعتبر (`415`) نیز اجرا شد. جریان End-to-End واقعی و benchmark کارایی باید پس از در دسترس‌بودن Docker daemon، Redis قرارداد، PostgreSQL و مدل embedding اجرا شود؛ تست mock جایگزین آن نیست.

## محدودیت‌های شناخته‌شده

- PDF اسکن‌شده بدون لایهٔ متن به OCR نیاز دارد و پشتیبانی نمی‌شود.
- دسته‌بندی، تشخیص امضا و تفکیک بندها قطعیت حقوقی ندارند و باید با دادهٔ برچسب‌خورده ارزیابی شوند.
- `confidence=0.9` قانون‌محور احتمال آماری کالیبره‌شده نیست.
- تحلیل ریسک، گزارش نهایی، سرویس پیامک و RAG کامل هنوز پیاده‌سازی نشده‌اند.
