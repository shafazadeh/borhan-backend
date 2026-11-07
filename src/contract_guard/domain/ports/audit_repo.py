from typing import Protocol


class AuditRepository(Protocol):
    def record(self, event: str) -> None: ...
