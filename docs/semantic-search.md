# جستجوی معنایی قرارداد

این قابلیت به PostgreSQL دارای افزونه pgvector، migrationهای پروژه، Redis برای ورود و وابستگی‌های `pip install -e .` نیاز دارد. تنظیمات اتصال در `.env` مشخص می‌شوند. راه‌اندازی مطابق README با `docker compose up -d postgres redis`، سپس `python -m contract_guard.infrastructure.database.migrate` و `python -m contract_guard` است. migration 005 در صورت وجود بردارهای غیر ۳۸۴بعدی متوقف می‌شود؛ پیش از مهاجرت داده‌های موجود را بررسی کنید. تنظیم پیش‌فرض `EMBEDDING_MODEL_NAME` برابر `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` و `EMBEDDING_MODEL_REVISION` برابر `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` است. اجرای اول ممکن است به دریافت فایل‌های مدل نیاز داشته باشد. تغییر مدل یا revision می‌تواند بردارهای موجود را ناسازگار کند و مستلزم برنامه‌ریزی برای بازتولید آنهاست.

مسیر `POST /api/v1/contracts/search` به access token معتبر Bearer نیاز دارد و فقط چانک‌های متعلق به همان کاربر را جستجو می‌کند. ابتدا با مسیرهای ورود توکن بگیرید، سپس در `/docs` گزینه Authorize را بزنید و توکن را وارد کنید. از بخش contracts، مسیر جستجو را باز کنید، Try it out را بزنید و نمونه را اجرا کنید. تعریف ماشین‌خوان در `/openapi.json` موجود است.

نمونه درخواست:

```json
{"query":"شرایط پرداخت قرارداد چیست؟","top_k":5}
```

نمونه پاسخ (مقادیر صرفاً نمونه هستند):

```json
[{"contract_id":"contract-1","chunk_id":"chunk-1","content":"پرداخت اقساط طبق توافق انجام می‌شود.","similarity":0.82}]
```

نتایج به ترتیب شباهت کسینوسی نزولی هستند؛ شباهت احتمال نیست. اگر نتیجه‌ای نباشد پاسخ `[]` است. مقدار `top_k` از ۱ تا ۱۰۰ مجاز است؛ `limit` نیز برای سازگاری با درخواست‌های قبلی پذیرفته می‌شود. برخی داده‌های قدیمی ممکن است `chunk_id` تهی داشته باشند. 401 نشان‌دهنده عدم احراز هویت، 422 ورودی نامعتبر، 500 ناسازگاری ابعاد و 503 خطای وابستگی است. ابعاد برابر، یکسان بودن مدل سازندهٔ داده‌های قدیمی را اثبات نمی‌کند؛ منشأ مدل داده‌های قدیمی باید جداگانه مشخص باشد.

اجرای تست‌ها در ویندوز:

```powershell
.\venv\Scripts\python.exe -m pytest -q tests/test_embedding.py tests/test_semantic_search.py tests/test_semantic_search_integration.py
```

برای تست یکپارچه، `TEST_DATABASE_URL` را به یک دیتابیس تست مستقل با migrationهای اعمال‌شده و افزونه pgvector تنظیم کنید و همان دستور را اجرا کنید. این تست از جدول موقت و rollback استفاده می‌کند؛ در نبود این متغیر skip می‌شود. هرگز آدرس دیتابیس تولید را برای تست وارد نکنید.

برای آزمون واقعی فارسی، دیتابیس تست باید نامی با پیشوند `contract_guard_search_test_` داشته باشد و متغیر `RUN_REAL_EMBEDDING_TEST=1` تنظیم شود. این آزمون از مدل واقعی، نشست Bearer واقعی و چند چانک فارسی استفاده می‌کند و کاربران آزمایشی خود را پاک می‌کند. اجرای آن ممکن است به بارگذاری زمان‌بر مدل نیاز داشته باشد:

```powershell
$env:TEST_DATABASE_URL = '<نشانی دیتابیس تست مستقل>'
$env:RUN_REAL_EMBEDDING_TEST = '1'
.\venv\Scripts\python.exe -m pytest -s -q tests/test_semantic_search_integration.py
```
