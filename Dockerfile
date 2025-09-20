
FROM python:3.11-slim

WORKDIR /

RUN pip install --no-cache-dir uv uvicorn

COPY pyproject.toml .
COPY README.md .
COPY . .

RUN uv venv

RUN uv pip compile --generate-hashes pyproject.toml > requirements.txt
RUN uv pip install -r requirements.txt

EXPOSE 8000

CMD [".venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


