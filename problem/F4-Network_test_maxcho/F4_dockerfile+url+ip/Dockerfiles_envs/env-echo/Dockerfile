FROM python:3.9-alpine

WORKDIR /app

ENV ECHO_MESSAGE="Hello from Echo Service!"

COPY server.py .

EXPOSE 9000

CMD ["python3", "server.py"]
