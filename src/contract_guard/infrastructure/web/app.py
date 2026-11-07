from fastapi import FastAPI
from contract_guard.infrastructure.web.v1.routes import router

app = FastAPI(title="Contract Guard")
app.include_router(router)
