FROM python:3.12-slim-bookworm

WORKDIR /app

COPY mock_api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY mock_api/ /app/mock_api/
COPY mock_assets/ /app/mock_assets/

ENV ASSETS_DIR=/app/mock_assets
ENV BASE_URL=http://localhost:8080

EXPOSE 8080

CMD ["uvicorn", "mock_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
