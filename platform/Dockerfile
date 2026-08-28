FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml requirements.txt ./
COPY migrate_framework ./migrate_framework
RUN pip install --no-cache-dir -e .
EXPOSE 8080 8501
CMD ["uvicorn", "migrate_framework.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
