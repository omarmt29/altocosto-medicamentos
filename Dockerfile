FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    gcc \
    libpq5 \
    cron \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sfn /usr/share/zoneinfo/America/Santo_Domingo /etc/localtime \
    && echo America/Santo_Domingo > /etc/timezone

ENV TZ=America/Santo_Domingo

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && grep -v -i '^pyodbc' requirements.txt > /tmp/requirements.docker.txt \
    && pip install --no-cache-dir -r /tmp/requirements.docker.txt

RUN python - << 'PY'
import io, os, tarfile, urllib.request
url = "https://download.docker.com/linux/static/stable/x86_64/docker-29.8.1.tgz"
print("descargando", url, flush=True)
data = urllib.request.urlopen(url, timeout=180).read()
with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
    src = tar.extractfile(tar.getmember("docker/docker"))
    with open("/usr/local/bin/docker", "wb") as out:
        out.write(src.read())
os.chmod("/usr/local/bin/docker", 0o755)
PY

COPY . /app
RUN chmod +x /app/docker/cron-entrypoint.sh /app/docker/run_scrape.sh

EXPOSE 8099

CMD ["python", "servir.py"]
