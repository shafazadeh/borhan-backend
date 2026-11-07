import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from python_multipart import MultipartParser
from python_multipart.exceptions import MultipartParseError
from python_multipart.multipart import parse_options_header
from contract_guard.application.use_cases.extract_document import extract_document
from contract_guard.application.use_cases.search_context import search_context
from contract_guard.application.use_cases.classify_clauses import HybridClauseClassifier
from contract_guard.config.settings import Settings
from contract_guard.domain.models.taxonomy import ClauseInput
from contract_guard.infrastructure.llm.taxonomy_gateway import LLMTaxonomyGateway
from contract_guard.infrastructure.web.dependencies import current_session

router = APIRouter()
FORMATS = {b"application/pdf": "pdf", b"application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx"}


@router.post("/contracts/extract", openapi_extra={"requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {"type": "object", "required": ["file"], "properties": {"file": {"type": "string", "format": "binary"}}}}}}})
async def extract_contract(request: Request, user=Depends(current_session)):
    content_type, options = parse_options_header(request.headers.get("content-type", ""))
    if content_type != b"multipart/form-data" or not options.get(b"boundary") or len(options[b"boundary"]) > 70:
        raise HTTPException(415, "Expected multipart form data")
    content, field, value = bytearray(), bytearray(), bytearray()
    headers = {}
    state = {"parts": 0, "header_size": 0, "complete": False}
    maximum = Settings().upload_max_bytes
    def part_begin():
        state["parts"] += 1
        if state["parts"] != 1: raise HTTPException(422, "Exactly one file is required")
    def header_field(data, start, end):
        field.extend(data[start:end]); state["header_size"] += end - start
        if state["header_size"] > 8192: raise HTTPException(413, "Multipart headers too large")
    def header_value(data, start, end):
        value.extend(data[start:end]); state["header_size"] += end - start
        if state["header_size"] > 8192: raise HTTPException(413, "Multipart headers too large")
    def header_end():
        key = bytes(field).lower()
        if key in headers: raise HTTPException(422, "Duplicate multipart header")
        headers[key] = bytes(value); field.clear(); value.clear()
    def headers_finished():
        disposition, params = parse_options_header(headers.get(b"content-disposition", b""))
        if disposition != b"form-data" or params.get(b"name") != b"file" or b"filename" not in params:
            raise HTTPException(422, "Exactly one file is required")
    def part_data(data, start, end):
        if len(content) + end - start > maximum: raise HTTPException(413, "File too large")
        content.extend(data[start:end])
    def finished(): state["complete"] = True
    parser = MultipartParser(options[b"boundary"], {"on_part_begin": part_begin, "on_header_field": header_field,
        "on_header_value": header_value, "on_header_end": header_end, "on_headers_finished": headers_finished,
        "on_part_data": part_data, "on_end": finished})
    try:
        received = 0
        async for chunk in request.stream():
            received += len(chunk)
            if received > maximum + 16384: raise HTTPException(413, "Request too large")
            parser.write(chunk)
        parser.finalize()
        if not state["complete"] or state["parts"] != 1 or not content: raise HTTPException(422, "Incomplete or empty file")
        kind = FORMATS.get(headers.get(b"content-type", b"").lower())
        if kind is None: raise HTTPException(415, "Only PDF and DOCX files are supported")
        result = await asyncio.to_thread(extract_document, bytes(content), kind)
        clauses = [ClauseInput.model_validate({key: item[key] for key in ("clause_id", "index", "article_title", "text")}) for item in result["clauses"]]
        classifications = await HybridClauseClassifier(LLMTaxonomyGateway(), Settings().taxonomy_llm_concurrency).classify_batch(clauses)
        for item, classification in zip(result["clauses"], classifications):
            item["taxonomy"] = classification.model_dump(mode="json")
            item["search_context"] = search_context(item["article_title"], classification.primary_category, item["text"])
        return result
    except MultipartParseError as exc:
        raise HTTPException(422, "Invalid multipart body") from exc
    finally:
        content.clear()
