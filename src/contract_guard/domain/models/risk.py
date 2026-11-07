from dataclasses import dataclass


@dataclass(frozen=True)
class Risk:
    level: str
    explanation: str
