# src/contract_guard/infrastructure/web/v1/endpoints/ingestion.py

- read_contract_upload · function · L18-L70 — async def read_contract_upload(request: Request, maximum: int) -> dict
- part_begin · function · L26-L28 — def part_begin()
- header_field · function · L29-L31 — def header_field(data, start, end)
- header_value · function · L32-L34 — def header_value(data, start, end)
- header_end · function · L35-L38 — def header_end()
- headers_finished · function · L39-L42 — def headers_finished()
- part_data · function · L43-L45 — def part_data(data, start, end)
- finished · function · L46-L46 — def finished()
- extract_contract · function · L74-L76 — async def extract_contract(request: Request, user=Depends(current_session))
