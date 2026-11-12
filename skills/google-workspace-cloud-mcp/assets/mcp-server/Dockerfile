# One image serves both roles: the Cloud Run *service* runs server.py, and the
# Cloud Run *job* runs harvester.py with --args="harvester.py". Same code, same
# config, no drift between what the server reads and what the harvester writes.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py auth.py policy.py kb.py workspace.py workspace_write.py harvester.py schema.sql ./

# Cloud Run injects PORT; the server reads it.
ENV PORT=8080
EXPOSE 8080

# Non-root: the container never needs to write anything to its own filesystem.
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

ENTRYPOINT ["python"]
CMD ["server.py"]
