import json
import os
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ModelServiceError(Exception):
    """The configured model service could not produce a valid response."""


class ModelServiceTimeout(ModelServiceError):
    pass


def classify_clause(clause: str) -> str:
    base_url = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "contract-risk-model")
    api_key = os.environ.get("LLM_API_KEY")
    try:
        timeout = float(os.environ.get("LLM_TIMEOUT_SECONDS", "120"))
        if timeout <= 0:
            raise ValueError
    except ValueError as exc:
        raise ModelServiceError("LLM_TIMEOUT_SECONDS must be a positive number") from exc

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": clause}],
        "temperature": 0,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.load(response)
        content = result["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty model response")
        return content
    except (TimeoutError, socket.timeout) as exc:
        raise ModelServiceTimeout("Model service timed out") from exc
    except HTTPError as exc:
        raise ModelServiceError(f"Model service returned HTTP {exc.code}") from exc
    except URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise ModelServiceTimeout("Model service timed out") from exc
        raise ModelServiceError("Could not connect to model service") from exc
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ModelServiceError("Model service returned an invalid response") from exc
