# Use lightweight official Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only requirements first to cache the library installation
COPY requirements.txt .

# Install libraries without saving unnecessary cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy all other files (including bot.py and .env)
COPY . .

# Run the bot (-u is needed so logs are immediately output to the Docker console)
CMD ["python", "-u", "bot.py"]