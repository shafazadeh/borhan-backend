from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from contextlib import asynccontextmanager
import asyncio
import logging

from app.config import Settings
from app.auth import router as auth_router
from app.contracts import router as contracts_router
from app.services.risk_classifier import ModelServiceError, ModelServiceTimeout, classify_clause


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = Settings.from_environment()
    app.state.model_semaphore = asyncio.Semaphore(app.state.settings.model_concurrency)
    logging.getLogger("uvicorn.access").disabled = True
    yield


app = FastAPI(title="Borhan API", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(contracts_router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": "Invalid request"})


@app.middleware("http")
async def safe_error_response(request, call_next):
    try:
        return await call_next(request)
    except Exception:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

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
