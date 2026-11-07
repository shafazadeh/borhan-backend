import uvicorn
from contract_guard.config.settings import Settings


def main():
    settings = Settings()
    uvicorn.run("contract_guard.infrastructure.web.app:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
