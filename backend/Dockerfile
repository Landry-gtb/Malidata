FROM python:3.11-slim

WORKDIR /app

# Installer dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# ÉTAPE 1 : Installer PyTorch d'abord
RUN pip install --no-cache-dir torch==2.2.2 --index-url https://download.pytorch.org/whl/cpu

# ÉTAPE 2 : Copier requirements et installer le reste
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir 'numpy<2.0' --force-reinstall

# ÉTAPE 3 : Copier le code (change souvent, ne casse pas le cache)
COPY . .

RUN mkdir -p /app/reports

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]