FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY init.sql .
COPY VERSION .
COPY templates/ templates/

# Create data directory for database
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Set environment variables
ENV DATA_DIR=/app/data
ENV PORT=8000

# Run the application
CMD ["python", "app.py"]
