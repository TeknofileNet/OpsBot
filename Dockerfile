#
# docker build . -t your-repo/bolt-app
#
FROM python:3.13-alpine AS builder

RUN apk add --no-cache \
    build-base \
    libffi-dev \
    openssl-dev \
    python3-dev \
    cargo

COPY requirements.txt /build/
WORKDIR /build/
RUN pip install --upgrade pip && pip install -r requirements.txt --no-cache-dir


FROM python:3.13-alpine
COPY --from=builder /build/ /app/
COPY --from=builder /usr/local/lib/ /usr/local/lib/

WORKDIR /app/
COPY *.py /app/

# The -u parameter in python (or python3 -u) forces the stdout,
# stderr, and stdin streams to be unbuffered. This means output
# is written immediately, which is especially useful for logging
# in Docker containers or when you want to see real-time output.

ENTRYPOINT ["python3", "-u", "app.py"]
