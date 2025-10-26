FROM python:3.12-alpine

WORKDIR /app

# for static analysis c libclang 
RUN apk add --no-cache clang-dev

# install dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
