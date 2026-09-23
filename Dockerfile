FROM python:3.13-slim-bookworm

ARG DEBIAN_FRONTEND=noninteractive
ENV ACCEPT_EULA=Y
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gcc \
    g++ \
    gnupg \
    libgssapi-krb5-2 \
    unixodbc \
    unixodbc-dev \
    && curl -sSL -O https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends msodbcsql17 \
    && odbcinst -q -d -n "ODBC Driver 17 for SQL Server" \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8765

CMD ["python", "servir.py"]
