FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
