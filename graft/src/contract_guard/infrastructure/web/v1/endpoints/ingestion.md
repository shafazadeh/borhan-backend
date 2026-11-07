# src/contract_guard/infrastructure/web/v1/endpoints/ingestion.py

- extract_contract · function · L19-L71 — async def extract_contract(request: Request, user=Depends(current_session))
- part_begin · function · L27-L29 — def part_begin()
- header_field · function · L30-L32 — def header_field(data, start, end)
- header_value · function · L33-L35 — def header_value(data, start, end)
- header_end · function · L36-L39 — def header_end()
- headers_finished · function · L40-L43 — def headers_finished()
- part_data · function · L44-L46 — def part_data(data, start, end)
- finished · function · L47-L47 — def finished()
