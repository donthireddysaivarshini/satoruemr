# Satoru EMR export service - read-only CouchDB -> Excel, served as a web page.
FROM python:3.12-slim

WORKDIR /app

COPY scripts/requirements.txt /app/scripts/requirements.txt
RUN pip install --no-cache-dir -r /app/scripts/requirements.txt

# the exporter reads form XMLs + translations at runtime (single source of
# truth shared with the Reports UI), so those must ship with it
COPY scripts/            /app/scripts/
COPY forms/app/          /app/forms/app/
COPY translations/       /app/translations/

ENV PYTHONUNBUFFERED=1
EXPOSE 8095

# COUCH_URL is supplied by compose
CMD ["sh", "-c", "python scripts/export_server.py --url \"$COUCH_URL\" --host 0.0.0.0 --port 8095 --base-path /exports"]
