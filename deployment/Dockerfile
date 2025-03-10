FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN cd core/src/orderbook && \
    g++ -shared -fPIC -o liborderbook.so limit_order_book.cpp

EXPOSE 8000 8001

CMD ["python", "dashboard/src/main.py"] 