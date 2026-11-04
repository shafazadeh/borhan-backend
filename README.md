# Borhan API

## تحلیل ریسک بند قرارداد

سرویس به یک API سازگار با OpenAI Chat Completions (برای مثال LiteLLM) متصل می‌شود. تنظیمات زیر را مطابق سرویس مدل تنظیم کنید:

- `LLM_BASE_URL`: آدرس پایهٔ API، بدون `/chat/completions`؛ پیش‌فرض `http://localhost:8000/v1`.
- `LLM_MODEL`: نام مدلی که سرویس می‌شناسد؛ پیش‌فرض `contract-risk-model`.
- `LLM_API_KEY`: کلید API، در صورت نیاز سرویس.
- `LLM_TIMEOUT_SECONDS`: مهلت پاسخ به ثانیه؛ پیش‌فرض `120`.

اگر مدل روی پورت ۸۰۰۰ اجرا می‌شود، بک‌اند را روی پورت دیگری اجرا کنید:

```powershell
$env:LLM_BASE_URL = "http://localhost:8000/v1"
$env:LLM_MODEL = "contract-risk-model"
.\venv\Scripts\python.exe -m uvicorn app.main:app --port 8001
```

درخواست `POST /api/v1/contract-risk`:

```json
{"clause": "کارفرما موظف است مبلغ قرارداد را ظرف ده روز پس از تحویل پرداخت کند."}
```

پاسخ شامل متن خام خروجی مدل است:

```json
{"result": "مناسب"}
```

مستندات تعاملی در `http://localhost:8001/docs` در دسترس است. این اتصال به سرویس Chat Completions نیاز دارد؛ خروجی و قابلیت ارائهٔ احتمال یا میزان اطمینان به سرویس و مدل بستگی دارد.
