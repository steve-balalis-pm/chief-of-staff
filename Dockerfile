FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for persistent data
RUN mkdir -p /app/data /app/logs

# Expose port
EXPOSE 8000

# Run the app (no auto-reload in production, no browser open)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
