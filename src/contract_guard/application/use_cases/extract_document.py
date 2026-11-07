import json
import os
import subprocess
import sys
from fastapi import HTTPException
from contract_guard.config.settings import Settings


def extract_document(data: bytes, kind: str):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "contract_guard.infrastructure.parsers.extraction_worker", kind],
            input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=Settings().extraction_timeout_seconds, check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        payload = json.loads(result.stdout)
        if "error" in payload:
            raise HTTPException(422, "Unable to extract document")
        return {"text": payload["text"], "closing_metadata": payload["closing_metadata"], "total_clauses": len(payload["clauses"]), "clauses": payload["clauses"]}
    except HTTPException:
        raise
    except (subprocess.SubprocessError, OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, "Unable to extract document") from exc
