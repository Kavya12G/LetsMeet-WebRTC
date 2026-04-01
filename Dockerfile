FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fix line endings on start.sh
RUN sed -i 's/\r//' start.sh && chmod +x start.sh

EXPOSE 8000

CMD ["sh", "start.sh"]
