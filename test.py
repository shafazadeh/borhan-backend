import json, urllib.request
def post(url, data):
    req = urllib.request.Request(url, data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)
print(post("http://localhost:8000/v1/chat/completions", {"model": "contract-risk-model",
      "messages": [{"role": "user", "content": "فسخ قرارداد بدون دلیل و بدون پرداخت"}]}))
print(post("http://localhost:8001/api/v1/contract-risk", {"clause": "پشتیبانی فنی و رفع باگها بر اساس آخرین استانداردهای برنامهنویسی"}))
