from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from app.services.risk_classifier import ModelServiceError, ModelServiceTimeout, classify_clause

app = FastAPI(title="Borhan API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClauseRequest(BaseModel):
    clause: str = Field(min_length=1, description="متن بند قرارداد")

    @field_validator("clause")
    @classmethod
    def validate_clause(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("متن بند قرارداد نمی‌تواند خالی باشد")
        return value


class ClauseResponse(BaseModel):
    result: str


@app.get("/")
def read_root():
    return {"status": "Borhan backend is up and running!"}


@app.post("/api/v1/contract-risk", response_model=ClauseResponse)
def analyze_contract_clause(request: ClauseRequest):
    try:
        return {"result": classify_clause(request.clause)}
    except ModelServiceTimeout as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ModelServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
