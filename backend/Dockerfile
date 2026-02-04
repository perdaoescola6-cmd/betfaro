FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Railway injects PORT at runtime
ENV PORT=8000

# Run via bash script
ENTRYPOINT ["./start.sh"]
