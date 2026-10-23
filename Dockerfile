FROM python:3.14-slim

# Install FFmpeg and system dependencies for voice support
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libffi-dev libnacl-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-u", "app.py"]
