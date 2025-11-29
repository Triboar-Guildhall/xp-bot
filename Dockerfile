FROM python:3.11-slim

WORKDIR /app

# Install system packages
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code and dashboard
COPY . .

# Set Python unbuffered mode
ENV PYTHONUNBUFFERED=1

# Default command runs the bot, but can be overridden
CMD ["python", "-u", "bot.py"]
