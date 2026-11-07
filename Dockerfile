FROM python:3.11-slim
WORKDIR /app
ENV PYTHONPATH=/app/src
COPY pyproject.toml README.md ./
COPY src ./src
COPY migrations ./migrations
RUN pip install --no-cache-dir .
CMD ["python", "-m", "contract_guard"]
