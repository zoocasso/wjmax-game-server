FROM python:3.12-slim

WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

# settings come from the environment at run time (docker run --env-file .env), never from the image
RUN useradd --create-home app
USER app

EXPOSE 8000
# behind Cloudflare: trust the forwarded client address
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
