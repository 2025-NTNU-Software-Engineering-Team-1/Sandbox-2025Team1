FROM python:3.9-alpine
WORKDIR /app
RUN echo "Hello from Server Container!" > index.html

CMD ["python3", "-m", "http.server", "8000"]