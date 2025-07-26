FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    fio \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8050
CMD ["python", "app.py"]