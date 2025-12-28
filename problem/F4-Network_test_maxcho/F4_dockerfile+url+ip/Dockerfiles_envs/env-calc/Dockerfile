FROM python:3.9-alpine

WORKDIR /app

ENV SERVICE_NAME="Calculator Service"

COPY server.py .

EXPOSE 9001

CMD ["python3", "server.py"]
