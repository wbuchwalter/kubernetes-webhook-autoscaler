FROM python:3-alpine

RUN apk --update add --virtual build-dependencies \
    python3-dev python-dev libffi-dev openssl-dev build-base && \
    pip install --upgrade pip cffi cryptography && \
    apk add --no-cache bash git && \
    rm -rf /var/cache/apk/*

COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r /app/requirements.txt

RUN apk del build-dependencies
RUN apk --update add libffi-dev

ENV FLASK_APP=main.py

EXPOSE 5000

COPY ./ /app/

ENTRYPOINT flask run --host=0.0.0.0 --port=5000