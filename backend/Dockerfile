FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway injects PORT at runtime (default 8000 for local dev)
ENV PORT=8000

# Run the application - run.py reads PORT from environment
CMD ["python", "run.py"]
