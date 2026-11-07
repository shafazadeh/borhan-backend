import json
import sys
from contract_guard.application.use_cases.clause_splitter import segment_clauses
from contract_guard.application.use_cases.extract_closing import extract_closing
from contract_guard.config.settings import Settings
from contract_guard.infrastructure.parsers.select_parser import select_parser


def main():
    try:
        kind = sys.argv[1]
        data = sys.stdin.buffer.read(Settings().upload_max_bytes + 1)
        if len(data) > Settings().upload_max_bytes:
            raise ValueError("File too large")
        text = select_parser(kind, data).extract(data)
        body, closing = extract_closing(text)
        print(json.dumps({"text": text, "closing_metadata": closing, "clauses": segment_clauses(body)}, ensure_ascii=True))
    except Exception:
        print(json.dumps({"error": "Unable to extract document"}))


if __name__ == "__main__":
    main()
