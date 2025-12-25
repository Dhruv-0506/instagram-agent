# Use a lightweight python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port (OnDemand usually expects port 5000 or 8080)
EXPOSE 5000

# Run the application using Gunicorn (Production Server)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
