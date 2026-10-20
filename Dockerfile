FROM python:3.12-slim

WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

# settings come from the environment at run time (docker run --env-file .env), never from the image
RUN useradd --create-home app
USER app

EXPOSE 8000
# The app never uses the client address, so X-Forwarded-For is ignored rather than trusted:
# requests reach the container from Cloudflare, not from a proxy on this host.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
