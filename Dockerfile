FROM python:3.11-slim
WORKDIR /app
ENV PYTHONPATH=/app/src
ENV TMPDIR=/tmp/contract-guard
COPY pyproject.toml README.md ./
COPY src ./src
COPY migrations ./migrations
RUN pip install --no-cache-dir .
RUN mkdir -p /tmp/contract-guard
CMD ["python", "-m", "contract_guard"]
