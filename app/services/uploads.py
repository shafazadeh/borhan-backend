from fastapi import HTTPException, Request
from python_multipart import MultipartParser
from python_multipart.exceptions import MultipartParseError
from python_multipart.multipart import parse_options_header


MAX_FILE_BYTES = 15 * 1024 * 1024
MAX_HEADER_BYTES = 16 * 1024


async def read_upload(request: Request) -> tuple[bytes, str]:
    content_type, options = parse_options_header(request.headers.get("content-type", ""))
    if content_type != b"multipart/form-data" or not options.get(b"boundary"):
        raise HTTPException(status_code=415, detail="Expected multipart form data")
    content = bytearray()
    field = bytearray()
    value = bytearray()
    headers = {}
    state = {"parts": 0, "header_size": 0, "complete": False}

    def part_begin():
        state["parts"] += 1
        if state["parts"] != 1:
            raise HTTPException(status_code=422, detail="Exactly one file is required")

    def header_field(data, start, end):
        field.extend(data[start:end])
        state["header_size"] += end - start
        if state["header_size"] > MAX_HEADER_BYTES:
            raise HTTPException(status_code=413, detail="Multipart headers too large")

    def header_value(data, start, end):
        value.extend(data[start:end])
        state["header_size"] += end - start
        if state["header_size"] > MAX_HEADER_BYTES:
            raise HTTPException(status_code=413, detail="Multipart headers too large")

    def header_end():
        name = bytes(field).lower()
        if name in headers:
            raise HTTPException(status_code=422, detail="Duplicate multipart header")
        headers[name] = bytes(value)
        field.clear()
        value.clear()

    def headers_finished():
        disposition, params = parse_options_header(headers.get(b"content-disposition", b""))
        if disposition != b"form-data" or params.get(b"name") != b"file" or b"filename" not in params:
            raise HTTPException(status_code=422, detail="Exactly one file is required")

    def part_data(data, start, end):
        if len(content) + end - start > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="File exceeds 15 MB")
        content.extend(data[start:end])

    def finished():
        state["complete"] = True

    parser = MultipartParser(options[b"boundary"], {
        "on_part_begin": part_begin,
        "on_header_field": header_field,
        "on_header_value": header_value,
        "on_header_end": header_end,
        "on_headers_finished": headers_finished,
        "on_part_data": part_data,
        "on_end": finished,
    })
    try:
        async for chunk in request.stream():
            parser.write(chunk)
        parser.finalize()
        if not state["complete"] or state["parts"] != 1 or not content:
            raise HTTPException(status_code=422, detail="Incomplete or empty file")
        declared_type = headers.get(b"content-type", b"").decode("ascii", errors="replace").lower()
        return bytes(content), declared_type
    except MultipartParseError:
        raise HTTPException(status_code=422, detail="Invalid multipart body") from None
    finally:
        content.clear()
